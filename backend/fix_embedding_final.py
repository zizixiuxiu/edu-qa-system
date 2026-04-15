"""修复 knowledge 表的 embedding 列 - 删除旧数据并重建"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 1. 删除旧的 embedding 列
        await conn.execute(text("""
            ALTER TABLE knowledge DROP COLUMN IF EXISTS embedding
        """))
        print("Dropped old embedding column")
        
        # 2. 删除可能存在的临时列
        await conn.execute(text("""
            ALTER TABLE knowledge DROP COLUMN IF EXISTS embedding_new
        """))
        print("Dropped temp column if exists")
        
        # 3. 添加新的 vector(384) 列
        await conn.execute(text("""
            ALTER TABLE knowledge ADD COLUMN embedding vector(384)
        """))
        print("Added new vector(384) column")
        
        print("Fix complete! The embedding column is now ready for new data.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
