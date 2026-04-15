"""数据库配置 - SQLModel + PostgreSQL + pgvector"""
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from pgvector.sqlalchemy import Vector
from typing import Optional, List
import numpy as np

from app.core.config import settings

# 同步引擎（用于初始化）
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={"connect_timeout": 10}
)

# 异步引擎（用于生产环境）
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_engine = create_async_engine(
    async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def init_db():
    """初始化数据库 - 创建表和扩展"""
    # 创建pgvector扩展
    with sync_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # 创建所有表
    SQLModel.metadata.create_all(sync_engine)


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


class VectorSearchMixin:
    """向量搜索混入类"""
    
    @classmethod
    async def similarity_search(
        cls,
        session: AsyncSession,
        embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List:
        """余弦相似度搜索"""
        # 使用pgvector的<=>操作符（余弦距离）
        # 距离 = 1 - 相似度，所以相似度 > threshold 相当于距离 < 1 - threshold
        distance_threshold = 1 - threshold
        
        statement = select(cls).where(
            cls.embedding.cosine_distance(embedding) < distance_threshold
        ).order_by(
            cls.embedding.cosine_distance(embedding)
        ).limit(top_k)
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    @classmethod
    async def check_duplicate(
        cls,
        session: AsyncSession,
        embedding: List[float],
        threshold: float = 0.92
    ) -> Optional:
        """检查是否重复"""
        distance_threshold = 1 - threshold
        
        statement = select(cls).where(
            cls.embedding.cosine_distance(embedding) < distance_threshold
        ).limit(1)
        
        result = await session.execute(statement)
        return result.scalar_one_or_none()
