"""
修复数据库表结构

删除旧表，让SQLModel重新创建（会丢失数据，仅用于开发环境）
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.infrastructure.database.connection import db


async def fix_database():
    """删除表并重新创建"""
    
    await db.connect()
    
    async with db.session() as session:
        print("⚠️  警告：此操作会删除所有数据！")
        print("正在删除旧表...")
        
        # 删除表（按依赖顺序）
        tables = [
            "benchmark_results",
            "knowledge_items",
            "sessions",
            "experts"
        ]
        
        for table in tables:
            try:
                await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"  ✅ 已删除 {table}")
            except Exception as e:
                print(f"  ⚠️  删除 {table} 失败: {e}")
        
        print("\n正在创建新表...")
    
    # 重新创建表
    await db.create_tables()
    print("\n✅ 数据库修复完成！")
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(fix_database())
