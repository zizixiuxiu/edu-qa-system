"""修复 knowledge 表的 content 列 - 改为普通列"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 1. 删除旧的 generated content 列
        await conn.execute(text("""
            ALTER TABLE knowledge DROP COLUMN IF EXISTS content
        """))
        print("Dropped old content column")
        
        # 2. 添加新的普通 content 列
        await conn.execute(text("""
            ALTER TABLE knowledge ADD COLUMN content TEXT
        """))
        print("Added new content column")
        
        # 3. 更新现有数据
        await conn.execute(text("""
            UPDATE knowledge SET content = COALESCE(question, '') || ' ' || COALESCE(answer, '')
            WHERE content IS NULL
        """))
        print("Updated existing data")
        
        print("修复完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
