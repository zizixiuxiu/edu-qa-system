"""
检查数据库向量维度
运行: python check_db_vector_dim.py
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, init_db

async def check_vector_dimension():
    """检查知识库表的向量维度"""
    print("🔍 检查数据库向量维度...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 检查表是否存在
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge'
                )
            """))
            exists = result.scalar()
            
            if not exists:
                print("  ℹ️ knowledge 表不存在，将在启动时自动创建")
                return
            
            # 检查向量列的维度
            result = await session.execute(text("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'knowledge'::regclass 
                AND attname = 'embedding'
            """))
            typmod = result.scalar()
            
            if typmod:
                # pgvector 的 typmod 存储的是维度
                dim = typmod
                print(f"  📊 当前向量维度: {dim}")
                
                if dim != 384:
                    print(f"  ⚠️  维度不匹配！期望 384，实际 {dim}")
                    print("  💡 建议: 运行 migrate_alter_vector_dim.py 修复")
                else:
                    print("  ✅ 向量维度正确 (384)")
            else:
                print("  ❌ 无法获取向量维度信息")
                
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

if __name__ == "__main__":
    init_db()
    asyncio.run(check_vector_dimension())
