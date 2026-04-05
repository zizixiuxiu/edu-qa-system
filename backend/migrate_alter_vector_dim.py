"""
修改数据库表结构 - 将 vector 列从 512 维改为 384 维
运行: python migrate_alter_vector_dim.py
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, init_db

async def alter_vector_dimension():
    """修改 knowledge 表的 embedding 列维度"""
    print("🔧 修改向量列维度 (512 -> 384)...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 删除旧的 knowledge 表（如果有）
            print("  1. 删除旧表结构...")
            await session.execute(text("DROP TABLE IF EXISTS knowledge CASCADE"))
            
            await session.commit()
            
            print("✅ 旧表已删除")
            print("\n💡 请重启后端服务，系统会自动创建新的 384 维表结构")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 修改失败: {e}")
            raise

if __name__ == "__main__":
    # 初始化数据库连接
    init_db()
    # 运行修改
    asyncio.run(alter_vector_dimension())
