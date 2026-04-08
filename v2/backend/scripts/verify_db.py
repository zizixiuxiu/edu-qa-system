"""验证数据库表结构"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.infrastructure.database.connection import db


async def verify():
    await db.connect()
    
    async with db.session() as session:
        # 检查experts表
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'experts'
        """))
        columns = [r[0] for r in result.fetchall()]
        print('✅ experts表列:')
        for col in columns:
            print(f'  - {col}')
        
        if 'status' in columns:
            print('\n✅ status字段已存在！')
        else:
            print('\n❌ status字段不存在')
        
        # 检查knowledge_items表
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'knowledge_items'
        """))
        columns = [r[0] for r in result.fetchall()]
        print(f'\n✅ knowledge_items表列数: {len(columns)}')
        if 'embedding' in columns:
            print('  - embedding字段已存在')
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(verify())
