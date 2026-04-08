"""完整修复 benchmark_results 表结构"""
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
        
        # 添加所有缺少的列
        columns_to_add = [
            ('dataset_id', 'INTEGER DEFAULT 1'),
            ('accuracy_score', 'DOUBLE PRECISION DEFAULT 0.0'),
            ('completeness_score', 'DOUBLE PRECISION DEFAULT 0.0'),
            ('educational_score', 'DOUBLE PRECISION DEFAULT 0.0'),
            ('overall_score', 'DOUBLE PRECISION DEFAULT 0.0'),
            ('suggestions', 'TEXT'),
            ('is_in_iteration_queue', 'BOOLEAN DEFAULT FALSE'),
            ('is_processed', 'BOOLEAN DEFAULT FALSE'),
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in columns:
                await conn.execute(text(f"""
                    ALTER TABLE benchmark_results ADD COLUMN {col_name} {col_type}
                """))
                print(f"已添加 {col_name} 列")
            else:
                print(f"{col_name} 列已存在")
        
        print("修复完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
