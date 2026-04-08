"""清理所有测试数据"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def cleanup():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 查看所有数据
        result = await conn.execute(text("""
            SELECT id, question, model_answer, created_at 
            FROM benchmark_results 
            ORDER BY id
        """))
        all_rows = result.fetchall()
        print(f"当前共有 {len(all_rows)} 条测试记录:")
        for row in all_rows:
            q = row[1][:40] if row[1] else 'NULL'
            a = row[2][:40] if row[2] else 'NULL'
            print(f"  ID={row[0]}: {q}... | {a}...")
        
        # 删除所有数据（重新开始）
        result = await conn.execute(text("DELETE FROM benchmark_results"))
        print(f"\n已删除 {result.rowcount} 条记录")
        
        # 重置序列
        await conn.execute(text("ALTER SEQUENCE benchmark_results_id_seq RESTART WITH 1"))
        print("已重置ID序列")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup())
