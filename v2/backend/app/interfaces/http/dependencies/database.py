"""数据库依赖"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.database.connection import db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖函数"""
    if db.session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with db.session() as session:
        yield session
