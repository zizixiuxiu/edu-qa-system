"""检查并清理重复数据"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        # 检查 benchmark_results 中的重复数据
        result = await conn.execute(text("""
            SELECT question, COUNT(*) as cnt 
            FROM benchmark_results 
            WHERE question IS NOT NULL 
            GROUP BY question 
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        
        if duplicates:
            print(f"找到 {len(duplicates)} 条重复的问题:")
            for q, cnt in duplicates:
                print(f"  重复 {cnt} 次: {q[:50] if q else 'NULL'}...")
        else:
            print("没有重复数据")
        
        # 查看最近插入的数据
        result = await conn.execute(text("""
            SELECT id, question, model_answer, created_at 
            FROM benchmark_results 
            ORDER BY id DESC 
            LIMIT 10
        """))
        recent = result.fetchall()
        print("\n最近10条数据:")
        for row in recent:
            print(f"  ID={row[0]}, question={row[1][:30] if row[1] else 'NULL'}..., model_answer={row[2][:30] if row[2] else 'NULL'}...")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
