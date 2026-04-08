import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        # 给 tier 列设置默认值
        await conn.execute('ALTER TABLE knowledge ALTER COLUMN tier SET DEFAULT 2')
        # 给现有 null 值设置为 2
        await conn.execute('UPDATE knowledge SET tier = 2 WHERE tier IS NULL')
        print('✅ Fixed tier column')
        # 检查表结构
        cols = await conn.fetch("SELECT column_name, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'knowledge' ORDER BY ordinal_position")
        print('\nKnowledge table columns:')
        for c in cols:
            print(f"  {c['column_name']}: nullable={c['is_nullable']}, default={c['column_default']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix())
