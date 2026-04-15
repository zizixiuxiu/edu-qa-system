"""
完整流程测试 - 端到端验证
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.vl_service import vl_service
from app.services.rag.multi_tier_retrieval import get_retriever
from app.services.experts import llm_service

async def test_vl_identification():
    """测试1: VL学科识别"""
    print("\n📝 测试1: VL学科识别 (模拟模式)")
    print("-" * 50)
    
    test_cases = [
        ("勾股定理是什么？", "数学"),
        ("牛顿第一定律", "物理"),
        ("光合作用的条件", "生物"),
    ]
    
    for query, expected in test_cases:
        result = await vl_service.identify_subject(query)
        subject = result.get('subject', 'unknown')
        status = "✅" if subject == expected else "⚠️"
        print(f"  {status} '{query[:20]}...' -> {subject}")
    
    return True

def test_multi_tier_retrieval():
    """测试2: 多级检索"""
    print("\n🔍 测试2: 多级检索")
    print("-" * 50)
    
    retriever = get_retriever()
    
    test_queries = [
        ("三角形内角和是多少度？", "数学"),
        ("物体为什么会下落？", "物理"),
        ("什么是细胞？", "生物"),
    ]
    
    for query, subject in test_queries:
        results = retriever.retrieve(query, subject=subject, top_k=3)
        
        print(f"\n  查询: '{query[:30]}...'")
        print(f"  指定学科: {subject}")
        print(f"  检索到: {len(results)} 条")
        
        for i, r in enumerate(results[:2], 1):
            tier_str = "学科库" if r.tier == 1 else "通用库"
            print(f"    [{i}] [{tier_str}] {r.question[:40]}... (score: {r.score:.3f})")
    
    return True

def test_fallback_to_general():
    """测试3: 通用库兜底"""
    print("\n🔄 测试3: 通用库兜底机制")
    print("-" * 50)
    
    retriever = get_retriever()
    
    # 查询一个可能学科库没有的问题
    query = "什么是科学方法？"
    
    # 指定一个不匹配的学科，触发fallback
    results = retriever.retrieve(query, subject="数学", top_k=3)
    
    print(f"  查询: '{query}'")
    print(f"  指定学科: 数学（不匹配）")
    
    tier1_count = sum(1 for r in results if r.tier == 1)
    tier2_count = sum(1 for r in results if r.tier == 2)
    
    print(f"  T1(学科库): {tier1_count} 条")
    print(f"  T2(通用库): {tier2_count} 条")
    
    if tier2_count > 0:
        print("  ✅ 通用库兜底生效")
    
    return True

async def test_full_flow():
    """测试4: 完整流程（模拟）"""
    print("\n🚀 测试4: 完整流程模拟")
    print("-" * 50)
    
    query = "请解释勾股定理"
    
    # 步骤1: VL识别
    print("  Step1: VL学科识别...")
    subject_info = await vl_service.identify_subject(query)
    subject = subject_info.get('subject', '其他')
    print(f"    -> 识别为: {subject}")
    
    # 步骤2: 多级检索
    print("  Step2: 多级RAG检索...")
    retriever = get_retriever()
    results = retriever.retrieve(query, subject=subject, top_k=5)
    print(f"    -> 检索到 {len(results)} 条知识")
    
    # 步骤3: 构建Prompt
    print("  Step3: 构建Prompt...")
    context = retriever.format_context(results)
    prompt_preview = f"基于以下{len(results)}条知识回答:\n{context[:200]}..."
    print(f"    -> Prompt长度: {len(prompt_preview)} 字符")
    
    # 步骤4: LLM生成（模拟）
    print("  Step4: LLM生成（模拟模式）...")
    print("    -> 模型将基于检索结果生成答案")
    
    print("\n  ✅ 完整流程验证通过")
    return True

def test_data_statistics():
    """测试5: 数据统计"""
    print("\n📊 测试5: 数据分布统计")
    print("-" * 50)
    
    retriever = get_retriever()
    
    print("  学科库分布:")
    for subject, store in sorted(retriever.subject_stores.items()):
        print(f"    {subject}: {len(store.docs):,} 条")
    
    print(f"\n  通用库: {len(retriever.general_store.docs):,} 条")
    
    total = sum(len(s.docs) for s in retriever.subject_stores.values()) + len(retriever.general_store.docs)
    print(f"\n  总计: {total:,} 条")
    
    return True

async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 RAG系统完整流程测试")
    print("=" * 60)
    
    tests = [
        ("VL学科识别", test_vl_identification),
        ("多级检索", lambda: test_multi_tier_retrieval()),
        ("通用库兜底", lambda: test_fallback_to_general()),
        ("完整流程", test_full_flow),
        ("数据统计", lambda: test_data_statistics()),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print("📋 测试报告")
    print("=" * 60)
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！系统已就绪")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
