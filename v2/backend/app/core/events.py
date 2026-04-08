"""事件总线 - 领域事件发布订阅"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Type, TypeVar
import asyncio
from collections import defaultdict


@dataclass(frozen=True)
class DomainEvent:
    """领域事件基类"""
    event_id: str = field(default_factory=lambda: f"evt_{datetime.utcnow().timestamp()}")
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            **{
                k: v for k, v in self.__dict__.items()
                if k not in ["event_id", "occurred_at"]
            }
        }


T = TypeVar("T", bound=DomainEvent)
EventHandler = Callable[[T], Any]


class EventBus(ABC):
    """事件总线抽象"""
    
    @abstractmethod
    def subscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """订阅事件"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """取消订阅"""
        pass
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """发布事件"""
        pass


class InMemoryEventBus(EventBus):
    """内存事件总线实现"""
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """订阅事件"""
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    async def publish(self, event: DomainEvent) -> None:
        """发布事件 - 异步调用所有处理器"""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            return
        
        # 并发执行所有处理器
        tasks = []
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    tasks.append(result)
            except Exception as e:
                # 记录错误但不影响其他处理器
                print(f"Event handler error: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# 全局事件总线实例
event_bus: EventBus = InMemoryEventBus()


def subscribe(event_type: Type[T]):
    """事件订阅装饰器"""
    def decorator(handler: EventHandler) -> EventHandler:
        event_bus.subscribe(event_type, handler)
        return handler
    return decorator


def publish_event(event: DomainEvent) -> None:
    """发布事件的便捷函数"""
    asyncio.create_task(event_bus.publish(event))
