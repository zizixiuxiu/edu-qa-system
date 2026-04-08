"""领域实体基类"""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class Entity(ABC):
    """领域实体基类 - 抽象类，不定义字段"""
    
    def __init__(self):
        self._id: Optional[int] = None
        self._created_at: Optional[datetime] = None
        self._updated_at: Optional[datetime] = None
    
    @property
    def id(self) -> Optional[int]:
        return self._id
    
    @id.setter
    def id(self, value: Optional[int]):
        self._id = value
    
    @property
    def created_at(self) -> Optional[datetime]:
        return self._created_at
    
    @created_at.setter
    def created_at(self, value: Optional[datetime]):
        self._created_at = value
    
    @property
    def updated_at(self) -> Optional[datetime]:
        return self._updated_at
    
    @updated_at.setter
    def updated_at(self, value: Optional[datetime]):
        self._updated_at = value
    
    def update_timestamp(self) -> None:
        """更新时间戳"""
        self._updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self._id,
            "created_at": self._created_at.isoformat() if self._created_at else None,
            "updated_at": self._updated_at.isoformat() if self._updated_at else None,
        }
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        # 如果都有 id，按 id 比较
        if self._id is not None and other._id is not None:
            return self._id == other._id
        # 如果都没有 id，使用对象身份比较
        return self is other
    
    def __hash__(self) -> int:
        return hash(self._id) if self._id else id(self)


class AggregateRoot(Entity):
    """聚合根基类"""
    
    def __init__(self):
        super().__init__()
        self._events: List[Any] = []
    
    def add_event(self, event: Any) -> None:
        """添加领域事件"""
        self._events.append(event)
    
    def clear_events(self) -> List[Any]:
        """清空并返回所有事件"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def events(self) -> List[Any]:
        """获取事件列表（只读）"""
        return self._events.copy()


class ValueObject:
    """值对象基类"""
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        return hash(tuple(self.__dict__.values()))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.__dict__.copy()
