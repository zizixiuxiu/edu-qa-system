"""
修复向量维度问题 - 清空知识库表，重新初始化
运行: python migrate_fix_vector_dim.py
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, init_db

async def fix_vector_dimension():
    """清空知识库表，解决维度不匹配问题"""
    print("🔧 修复向量维度问题...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 清空知识库表
            print("  1. 清空 knowledge 表...")
            await session.execute(text("TRUNCATE TABLE knowledge CASCADE"))
            
            # 2. 重置专家的知识计数
            print("  2. 重置专家知识计数...")
            await session.execute(text("UPDATE experts SET knowledge_count = 0"))
            
            await session.commit()
            
            print("✅ 修复完成！")
            print("   - 知识库已清空")
            print("   - 专家计数已重置")
            print("\n💡 现在所有数据都将使用 384 维向量")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 修复失败: {e}")
            raise

if __name__ == "__main__":
    # 初始化数据库连接
    init_db()
    # 运行修复
    asyncio.run(fix_vector_dimension())
