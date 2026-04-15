#!/usr/bin/env python3
"""测试 GAOKAO 数据导入"""
import asyncio
import sys
import os

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

os.environ.setdefault("GAOKAO_BENCH_PATH", "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main")

from app.core.database import AsyncSessionLocal, init_db
from app.models.database import BenchmarkDataset
from sqlalchemy import select

async def test_import():
    """测试导入"""
    print("🧪 测试 GAOKAO 数据导入")
    print("=" * 50)
    
    # 初始化数据库
    print("\n1. 初始化数据库...")
    try:
        init_db()
        print("   ✅ 数据库初始化成功")
    except Exception as e:
        print(f"   ❌ 数据库初始化失败: {e}")
        return
    
    # 测试导入一道题
    async with AsyncSessionLocal() as session:
        print("\n2. 测试插入单条数据...")
        try:
            test_dataset = BenchmarkDataset(
                question="测试题目",
                correct_answer="A",
                subject="数学",
                year="2023",
                category="测试",
                score=5,
                analysis="测试解析",
                question_type="objective",
                source_url="file://test"
            )
            session.add(test_dataset)
            await session.commit()
            print("   ✅ 单条插入成功")
            
            # 清理测试数据
            await session.delete(test_dataset)
            await session.commit()
            print("   ✅ 测试数据已清理")
            
        except Exception as e:
            print(f"   ❌ 插入失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 检查现有数据
    async with AsyncSessionLocal() as session:
        print("\n3. 检查现有数据...")
        result = await session.execute(select(BenchmarkDataset))
        count = len(result.scalars().all())
        print(f"   当前共有 {count} 道题目")
    
    print("\n" + "=" * 50)
    print("测试完成!")

if __name__ == "__main__":
    asyncio.run(test_import())
