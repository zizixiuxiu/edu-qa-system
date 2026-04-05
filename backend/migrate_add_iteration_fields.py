"""
添加迭代队列字段到 benchmark_results 表
运行: python migrate_add_iteration_fields.py
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, init_db

async def add_iteration_fields():
    """添加 is_in_iteration_queue 和 is_processed 字段"""
    print("🔧 添加迭代队列字段...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 检查字段是否已存在
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'benchmark_results' 
                AND column_name = 'is_in_iteration_queue'
            """))
            
            if result.scalar():
                print("  ✓ 字段已存在")
                return
            
            # 添加 is_in_iteration_queue 字段
            print("  1. 添加 is_in_iteration_queue 字段...")
            await session.execute(text("""
                ALTER TABLE benchmark_results 
                ADD COLUMN is_in_iteration_queue BOOLEAN DEFAULT FALSE
            """))
            
            # 添加 is_processed 字段
            print("  2. 添加 is_processed 字段...")
            await session.execute(text("""
                ALTER TABLE benchmark_results 
                ADD COLUMN is_processed BOOLEAN DEFAULT FALSE
            """))
            
            await session.commit()
            print("✅ 字段添加成功！")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 添加失败: {e}")
            # 如果失败，尝试删除表重建
            print("\n⚠️  尝试删除表重建...")
            try:
                await session.execute(text("DROP TABLE IF EXISTS benchmark_results CASCADE"))
                await session.commit()
                print("✅ 表已删除，重启后端后会自动重建")
            except Exception as e2:
                print(f"❌ 删除表也失败: {e2}")

if __name__ == "__main__":
    init_db()
    asyncio.run(add_iteration_fields())
