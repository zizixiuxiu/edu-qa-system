"""仓储模式接口"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class Repository(ABC, Generic[T, ID]):
    """仓储接口基类"""
    
    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[T]:
        """获取所有实体"""
        pass
    
    @abstractmethod
    async def add(self, entity: T) -> T:
        """添加实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def exists(self, id: ID) -> bool:
        """检查实体是否存在"""
        pass


class UnitOfWork(ABC):
    """工作单元接口"""
    
    @abstractmethod
    async def __aenter__(self):
        """异步上下文进入"""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """提交事务"""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """回滚事务"""
        pass
