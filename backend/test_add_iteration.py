"""测试 add_to_iteration 功能"""
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test():
    # 检查 benchmark_results 状态
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        # 查看有多少错题可以加入
        results = await conn.fetch('''
            SELECT id, dataset_id, expert_id, is_correct, is_in_iteration_queue 
            FROM benchmark_results 
            WHERE is_correct = FALSE
            LIMIT 5
        ''')
        print(f"找到 {len(results)} 道错题:")
        for r in results:
            print(f"  ID={r['id']}, dataset_id={r['dataset_id']}, expert_id={r['expert_id']}, in_queue={r['is_in_iteration_queue']}")
        
        # 查看知识库数量
        count = await conn.fetchval('SELECT COUNT(*) FROM knowledge')
        print(f"\n当前知识库: {count} 条")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
