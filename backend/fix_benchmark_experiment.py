"""修复 benchmark_results 表 - experiment_mode 列设为 nullable"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 使 experiment_mode 列为 nullable
        await conn.execute(text("""
            ALTER TABLE benchmark_results ALTER COLUMN experiment_mode DROP NOT NULL
        """))
        print("experiment_mode 列现为 nullable")
        
        print("修复完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
