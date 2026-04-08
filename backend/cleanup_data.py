"""清理知识库和评测数据，重新开始"""
import asyncio
import asyncpg

async def cleanup():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        print("=== 开始清理数据 ===\n")
        
        # 1. 清空知识库数据
        count = await conn.fetchval('SELECT COUNT(*) FROM knowledge')
        await conn.execute('DELETE FROM knowledge')
        print(f"✅ 已清空 knowledge 表: {count} 条记录")
        
        # 重置序列（可选，让ID从1开始）
        await conn.execute("ALTER SEQUENCE knowledge_id_seq RESTART WITH 1")
        print("✅ 已重置 knowledge ID 序列")
        
        # 2. 重置专家知识计数
        await conn.execute('UPDATE experts SET knowledge_count = 0, tier0_count = 0')
        print("✅ 已重置专家知识计数")
        
        # 3. 重置 benchmark_results 的迭代状态
        count = await conn.fetchval('SELECT COUNT(*) FROM benchmark_results WHERE is_in_iteration_queue = TRUE')
        await conn.execute('''
            UPDATE benchmark_results 
            SET is_in_iteration_queue = FALSE, 
                is_processed = FALSE
            WHERE is_in_iteration_queue = TRUE
        ''')
        print(f"✅ 已重置 {count} 条 benchmark_results 的迭代状态")
        
        # 4. 可选：清空所有 benchmark_results（如果你想重新跑评测）
        # count = await conn.fetchval('SELECT COUNT(*) FROM benchmark_results')
        # await conn.execute('DELETE FROM benchmark_results')
        # print(f"✅ 已清空 benchmark_results: {count} 条记录")
        
        # 5. 可选：清空所有 benchmark_datasets（如果你想重新导入题目）
        # count = await conn.fetchval('SELECT COUNT(*) FROM benchmark_datasets')
        # await conn.execute('DELETE FROM benchmark_datasets')
        # print(f"✅ 已清空 benchmark_datasets: {count} 条记录")
        
        print("\n=== 清理完成 ===")
        print("\n当前状态:")
        knowledge_count = await conn.fetchval('SELECT COUNT(*) FROM knowledge')
        results_count = await conn.fetchval('SELECT COUNT(*) FROM benchmark_results')
        datasets_count = await conn.fetchval('SELECT COUNT(*) FROM benchmark_datasets')
        print(f"  - 知识库: {knowledge_count} 条")
        print(f"  - 评测结果: {results_count} 条")
        print(f"  - 评测数据集: {datasets_count} 条")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
