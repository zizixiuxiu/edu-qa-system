"""
创建pgvector索引脚本

运行此脚本创建论文中推荐的IVFFlat向量索引
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.infrastructure.database.connection import db
from app.core.config import get_settings

settings = get_settings()


async def create_vector_indexes():
    """创建向量索引和复合索引"""
    
    await db.connect()
    
    async with db.session() as session:
        print("🔧 创建pgvector扩展...")
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        print("🔧 创建IVFFlat向量索引 (nlist=100)...")
        # IVFFlat索引适合中等规模数据（1万-100万条）
        try:
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_ivfflat 
                ON knowledge_items 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            print("  ✅ IVFFlat索引创建成功")
        except Exception as e:
            print(f"  ⚠️ IVFFlat索引创建失败（可能已存在）: {e}")
        
        print("🔧 创建复合索引 (expert_id + tier + quality_score)...")
        try:
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_expert_tier_quality 
                ON knowledge_items (expert_id, tier, quality_score)
            """))
            print("  ✅ 复合索引创建成功")
        except Exception as e:
            print(f"  ⚠️ 复合索引创建失败（可能已存在）: {e}")
        
        print("🔧 创建相似度查询索引...")
        try:
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_tier_lookup 
                ON knowledge_items (tier, expert_id)
            """))
            print("  ✅ 层级查询索引创建成功")
        except Exception as e:
            print(f"  ⚠️ 层级查询索引创建失败（可能已存在）: {e}")
        
        print("\n📊 索引统计:")
        result = await session.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'knowledge_items'
        """))
        indexes = result.fetchall()
        for idx in indexes:
            print(f"  - {idx.indexname}")
    
    await db.disconnect()
    print("\n✅ 所有索引创建完成！")


if __name__ == "__main__":
    asyncio.run(create_vector_indexes())
