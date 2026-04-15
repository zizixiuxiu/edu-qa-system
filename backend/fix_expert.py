import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        # Delete the unrelated expert
        await conn.execute("DELETE FROM experts WHERE subject LIKE '%2010-2013%'")
        print('Deleted 2010-2013_English expert')
        
        # Show remaining experts
        experts = await conn.fetch('SELECT id, subject, name FROM experts ORDER BY id')
        print('\nRemaining experts:')
        for e in experts:
            print(f'  ID={e["id"]}, subject={e["subject"]}, name={e["name"]}')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix())
