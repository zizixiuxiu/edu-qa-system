"""迁移 knowledge 表结构以匹配模型"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def migrate():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 检查现有列
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'knowledge'
        """))
        columns = [row[0] for row in result.fetchall()]
        print(f"现有列: {columns}")
        
        # 添加新列（如果不存在）
        if 'content' not in columns:
            await conn.execute(text("""
                ALTER TABLE knowledge ADD COLUMN content TEXT 
                GENERATED ALWAYS AS (COALESCE(question, '') || ' ' || COALESCE(answer, '')) STORED
            """))
            print("已添加 content 列")
        
        if 'metadata' not in columns:
            await conn.execute(text("""
                ALTER TABLE knowledge ADD COLUMN metadata JSONB DEFAULT '{}'
            """))
            print("已添加 metadata 列")
        
        if 'source_type' not in columns:
            await conn.execute(text("""
                ALTER TABLE knowledge ADD COLUMN source_type VARCHAR DEFAULT 'generated'
            """))
            print("已添加 source_type 列")
            
        if 'usage_count' not in columns:
            await conn.execute(text("""
                ALTER TABLE knowledge ADD COLUMN usage_count INTEGER DEFAULT 0
            """))
            print("已添加 usage_count 列")
        
        print("迁移完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
