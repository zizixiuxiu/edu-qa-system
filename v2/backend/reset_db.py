"""重置数据库 - 删除所有表并重新创建"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from app.core.config import get_settings

settings = get_settings()

async def reset_database():
    """删除所有表并重新创建"""
    engine = create_async_engine(str(settings.DATABASE_URL))
    
    async with engine.begin() as conn:
        # 删除所有表
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("✅ 所有表已删除")
        
        # 重新创建表
        from app.infrastructure.database.models import ExpertDB, KnowledgeDB, SessionDB, BenchmarkResultDB
        await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ 所有表已重新创建")
    
    await engine.dispose()
    print("✅ 数据库重置完成")

if __name__ == "__main__":
    asyncio.run(reset_database())
