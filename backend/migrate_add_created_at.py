"""
数据库迁移脚本 - 为 training_jobs 表添加 created_at 字段
"""
import asyncio
import asyncpg
import os

# 数据库连接 URL（从环境变量或配置读取）
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/edu_qa")

async def migrate():
    """添加 created_at 字段到 training_jobs 表"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 检查字段是否已存在
        result = await conn.fetchval("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'training_jobs' AND column_name = 'created_at'
        """)
        
        if result:
            print("✓ created_at 字段已存在，无需迁移")
            return
        
        # 添加字段
        await conn.execute("""
            ALTER TABLE training_jobs 
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        
        print("✓ 成功添加 created_at 字段到 training_jobs 表")
        
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
