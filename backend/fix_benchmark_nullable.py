"""修复 benchmark_results 表 - 使列为 nullable"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 使列为 nullable
        await conn.execute(text("""
            ALTER TABLE benchmark_results ALTER COLUMN question DROP NOT NULL
        """))
        print("question 列现为 nullable")
        
        await conn.execute(text("""
            ALTER TABLE benchmark_results ALTER COLUMN correct_answer DROP NOT NULL
        """))
        print("correct_answer 列现为 nullable")
        
        await conn.execute(text("""
            ALTER TABLE benchmark_results ALTER COLUMN subject DROP NOT NULL
        """))
        print("subject 列现为 nullable")
        
        print("修复完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
