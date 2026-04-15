"""清理测试失败的脏数据"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def cleanup():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 查询失败的数据
        result = await conn.execute(text("""
            SELECT id, model_answer, created_at FROM benchmark_results 
            WHERE model_answer LIKE '[回答生成失败]%'
        """))
        failed_rows = result.fetchall()
        print(f"找到 {len(failed_rows)} 条失败的测试记录:")
        for row in failed_rows:
            print(f"  ID={row[0]}, created_at={row[2]}")
        
        # 删除失败的数据
        if failed_rows:
            result = await conn.execute(text("""
                DELETE FROM benchmark_results 
                WHERE model_answer LIKE '[回答生成失败]%'
            """))
            print(f"已删除 {result.rowcount} 条失败的测试记录")
        
        # 同时清理 model_answer 为 null 或空的问题记录
        result = await conn.execute(text("""
            SELECT id, model_answer FROM benchmark_results 
            WHERE model_answer IS NULL OR model_answer = ''
        """))
        empty_rows = result.fetchall()
        if empty_rows:
            print(f"找到 {len(empty_rows)} 条空回答记录")
            result = await conn.execute(text("""
                DELETE FROM benchmark_results 
                WHERE model_answer IS NULL OR model_answer = ''
            """))
            print(f"已删除 {result.rowcount} 条空记录")
        
        print("清理完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup())
