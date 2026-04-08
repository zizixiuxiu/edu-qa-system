"""修复 knowledge 表的 embedding 列类型"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 1. 添加新列
        await conn.execute(text("""
            ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS embedding_new vector(384)
        """))
        print("Added embedding_new column")
        
        # 2. 将数据从旧列转换到新列
        await conn.execute(text("""
            UPDATE knowledge 
            SET embedding_new = embedding::vector(384)
            WHERE embedding IS NOT NULL AND embedding_new IS NULL
        """))
        print("Converted data to new column")
        
        # 3. 删除旧列
        await conn.execute(text("""
            ALTER TABLE knowledge DROP COLUMN IF EXISTS embedding
        """))
        print("Dropped old embedding column")
        
        # 4. 重命名新列
        await conn.execute(text("""
            ALTER TABLE knowledge RENAME COLUMN embedding_new TO embedding
        """))
        print("Renamed column to embedding")
        
        print("Fix complete!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
