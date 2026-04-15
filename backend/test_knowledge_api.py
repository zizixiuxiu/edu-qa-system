import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:15432/edu_qa')
    try:
        rows = await conn.fetch('SELECT id, expert_id, question, answer, content, source_type FROM knowledge LIMIT 2')
        print(f'Found {len(rows)} knowledge records:')
        for r in rows:
            print(f'  ID={r["id"]}, expert={r["expert_id"]}, source={r["source_type"]}')
            q = r["question"][:50] if r["question"] else None
            c = r["content"][:50] if r["content"] else None
            print(f'    question={q}...')
            print(f'    content={c}...')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
