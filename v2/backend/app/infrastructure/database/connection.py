"""数据库连接管理"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from ...core.config import get_settings
from ...core.logging import LoggerMixin, get_logger

settings = get_settings()
logger = get_logger("database")


class Database(LoggerMixin):
    """数据库管理类"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_maker = None
    
    async def connect(self) -> None:
        """建立数据库连接"""
        self.engine = create_async_engine(
            self.database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,  # 自动检测连接有效性
        )
        
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self.logger.info(f"Database connected: {self.database_url.replace('://', '://***@')}")
    
    async def disconnect(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Database disconnected")
    
    async def create_tables(self) -> None:
        """创建所有表"""
        from .models import ExpertDB, KnowledgeDB, SessionDB, BenchmarkResultDB
        
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        self.logger.info("Database tables created")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器"""
        if not self.session_maker:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI依赖用的会话生成器"""
        if not self.session_maker:
            raise RuntimeError("Database not connected")
        
        async with self.session_maker() as session:
            try:
                yield session
            finally:
                await session.close()


# 全局数据库实例
db = Database(str(settings.DATABASE_URL))


async def init_database() -> None:
    """初始化数据库"""
    await db.connect()
    await db.create_tables()


async def close_database() -> None:
    """关闭数据库"""
    await db.disconnect()
