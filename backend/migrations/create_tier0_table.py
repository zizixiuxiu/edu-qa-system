"""
数据库迁移脚本 - 创建Tier 0知识库表

功能：
1. 创建 tier0_knowledge 表
2. 创建相关索引（包括pgvector向量索引）
3. 补充 sessions 表字段
4. 补充 experts 表字段
"""
import os
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
import logging

# 常量定义
MIN_DATA_FOR_IVFFLAT = 100  # 创建ivfflat索引的最小数据量

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库连接字符串（从环境变量读取，保留默认值）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:15432/edu_qa"
)


def migrate() -> bool:
    """
    执行数据库迁移
    
    Returns:
        bool: 迁移成功返回 True，失败返回 False
    """
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.begin() as conn:  # 自动事务管理
            logger.info("🔄 开始数据库迁移...")
            
            # 1. 创建 tier0_knowledge 表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS tier0_knowledge (
                id SERIAL PRIMARY KEY,
                expert_id INTEGER NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                embedding VECTOR(384),
                metadata JSONB DEFAULT '{}',
                quality_score FLOAT NOT NULL,
                accuracy_score FLOAT,
                completeness_score FLOAT,
                educational_score FLOAT,
                additional_score FLOAT,
                dedup_hash VARCHAR(64),
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            conn.execute(text(create_table_sql))
            logger.info("✅ tier0_knowledge 表创建成功")
            
            # 2. 创建基础索引
            create_basic_indexes_sql = """
            CREATE INDEX IF NOT EXISTS idx_tier0_expert_id ON tier0_knowledge(expert_id);
            CREATE INDEX IF NOT EXISTS idx_tier0_quality_score ON tier0_knowledge(quality_score);
            CREATE INDEX IF NOT EXISTS idx_tier0_dedup_hash ON tier0_knowledge(dedup_hash);
            CREATE INDEX IF NOT EXISTS idx_tier0_created_at ON tier0_knowledge(created_at DESC);
            """
            conn.execute(text(create_basic_indexes_sql))
            logger.info("✅ 基础索引创建成功")
            
            # 3. 创建pgvector向量索引（ivfflat）
            # 先检查表中是否有足够的数据
            check_count_sql = "SELECT COUNT(*) FROM tier0_knowledge;"
            result = conn.execute(text(check_count_sql))
            row_count = result.scalar() or 0
            
            # 删除已存在的向量索引（如果存在）
            drop_vector_index_sql = "DROP INDEX IF EXISTS idx_tier0_embedding;"
            conn.execute(text(drop_vector_index_sql))
            
            if row_count >= MIN_DATA_FOR_IVFFLAT:
                # 数据量足够，创建ivfflat索引
                create_vector_index_sql = """
                CREATE INDEX idx_tier0_embedding ON tier0_knowledge 
                USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                """
                conn.execute(text(create_vector_index_sql))
                logger.info("✅ 向量索引创建成功")
            else:
                # 数据量太小，先创建简单索引，后续可以重建
                logger.info("⚠️  tier0_knowledge 表数据量太小（{}条），跳过ivfflat向量索引".format(row_count))
                logger.info("   建议：数据量达到{}条后，手动执行重建向量索引".format(MIN_DATA_FOR_IVFFLAT))
            
            # 4. 补充 sessions 表字段
            alter_sessions_sql = """
            ALTER TABLE sessions 
            ADD COLUMN IF NOT EXISTS knowledge_type VARCHAR(20),
            ADD COLUMN IF NOT EXISTS additional_score FLOAT;
            """
            conn.execute(text(alter_sessions_sql))
            logger.info("✅ sessions 表字段补充成功")
            
            # 5. 补充 experts 表字段
            alter_experts_sql = """
            ALTER TABLE experts 
            ADD COLUMN IF NOT EXISTS tier0_count INTEGER DEFAULT 0;
            """
            conn.execute(text(alter_experts_sql))
            logger.info("✅ experts 表 tier0_count 字段添加成功")
            
            logger.info("🎉 数据库迁移完成！")
            return True
            
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
