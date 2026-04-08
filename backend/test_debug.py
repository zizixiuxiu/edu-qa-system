import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import get_session
from app.api.benchmark import add_to_iteration, AddToIterationRequest

async def test():
    try:
        async for session in get_session():
            request = AddToIterationRequest(result_ids=[1])
            result = await add_to_iteration(request, session)
            print('Result:', result)
            break
    except Exception as e:
        import traceback
        print('Error:', e)
        traceback.print_exc()

asyncio.run(test())
