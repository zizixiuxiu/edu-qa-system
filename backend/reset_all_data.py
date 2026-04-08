"""清空所有测试数据 - 重置数据库到初始状态"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def reset():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@localhost:15432/edu_qa')
    
    async with engine.begin() as conn:
        print("=== 清空数据表 ===")
        
        # 清空测试结果
        result = await conn.execute(text("DELETE FROM benchmark_results"))
        print(f"✅ benchmark_results: 删除 {result.rowcount} 条记录")
        await conn.execute(text("ALTER SEQUENCE benchmark_results_id_seq RESTART WITH 1"))
        
        # 清空测试数据集
        result = await conn.execute(text("DELETE FROM benchmark_datasets"))
        print(f"✅ benchmark_datasets: 删除 {result.rowcount} 条记录")
        await conn.execute(text("ALTER SEQUENCE benchmark_datasets_id_seq RESTART WITH 1"))
        
        # 清空 Tier0 知识库
        result = await conn.execute(text("DELETE FROM tier0_knowledge"))
        print(f"✅ tier0_knowledge: 删除 {result.rowcount} 条记录")
        await conn.execute(text("ALTER SEQUENCE tier0_knowledge_id_seq RESTART WITH 1"))
        
        # 清空普通知识库
        result = await conn.execute(text("DELETE FROM knowledge"))
        print(f"✅ knowledge: 删除 {result.rowcount} 条记录")
        await conn.execute(text("ALTER SEQUENCE knowledge_id_seq RESTART WITH 1"))
        
        # 清空会话记录
        result = await conn.execute(text("DELETE FROM sessions"))
        print(f"✅ sessions: 删除 {result.rowcount} 条记录")
        await conn.execute(text("ALTER SEQUENCE sessions_id_seq RESTART WITH 1"))
        
        # 重置专家统计
        await conn.execute(text("UPDATE experts SET knowledge_count = 0, tier0_count = 0"))
        print(f"✅ experts: 重置知识计数为 0")
        
        print("\n=== 数据已清空，可以重新开始测试 ===")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset())
