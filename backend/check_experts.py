import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        experts = await conn.fetch('SELECT id, subject, name FROM experts ORDER BY id')
        print('Experts in database:')
        for e in experts:
            print(f'  ID={e["id"]}, subject={e["subject"]}, name={e["name"]}')
            
        # Check knowledge count
        print('\nKnowledge count:')
        count = await conn.fetchval('SELECT COUNT(*) FROM knowledge')
        print(f'  Total: {count}')
        
        # Check by source
        sources = await conn.fetch('SELECT source_type, COUNT(*) FROM knowledge GROUP BY source_type')
        for s in sources:
            print(f'  {s["source_type"]}: {s["count"]}')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
