"""修复 benchmark_results 表结构"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 检查现有列
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'benchmark_results'
        """))
        columns = [row[0] for row in result.fetchall()]
        print(f"现有列: {columns}")
        
        # 添加缺少的列
        if 'dataset_id' not in columns:
            await conn.execute(text("""
                ALTER TABLE benchmark_results ADD COLUMN dataset_id INTEGER DEFAULT 1
            """))
            print("已添加 dataset_id 列")
        
        if 'is_correct' not in columns:
            await conn.execute(text("""
                ALTER TABLE benchmark_results ADD COLUMN is_correct BOOLEAN DEFAULT FALSE
            """))
            print("已添加 is_correct 列")
        
        if 'is_in_iteration_queue' not in columns:
            await conn.execute(text("""
                ALTER TABLE benchmark_results ADD COLUMN is_in_iteration_queue BOOLEAN DEFAULT FALSE
            """))
            print("已添加 is_in_iteration_queue 列")
        
        if 'is_processed' not in columns:
            await conn.execute(text("""
                ALTER TABLE benchmark_results ADD COLUMN is_processed BOOLEAN DEFAULT FALSE
            """))
            print("已添加 is_processed 列")
        
        print("修复完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
