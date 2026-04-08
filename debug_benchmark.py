#!/usr/bin/env python
"""调试基准测试错误"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from app.core.database import AsyncSessionLocal
from app.models.database import BenchmarkResult
from sqlalchemy import select

async def test_db():
    async with AsyncSessionLocal() as session:
        try:
            # 测试查询
            result = await session.execute(select(BenchmarkResult).limit(1))
            row = result.scalar_one_or_none()
            print(f"查询成功: {row}")
            
            # 测试插入
            test_result = BenchmarkResult(
                dataset_id=1,
                expert_id=1,
                model_answer="test",
                is_correct=True,
                experiment_config="routing=False,rag=False",
                experiment_id=None
            )
            session.add(test_result)
            await session.commit()
            print(f"插入成功: id={test_result.id}")
            
        except Exception as e:
            import traceback
            print(f"错误: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db())
