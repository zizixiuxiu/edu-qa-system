"""
新功能演示脚本

演示 VLM分类、RAG检索、云端质检 的使用
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.infrastructure.llm.vlm_service import vlm_service
from app.infrastructure.embedding.bge_encoder import get_encoder, encode_text
from app.domain.services.rag_service import get_retriever
from app.application.services.quality_service import get_quality_checker, CloudQualityChecker


async def demo_vlm_classification():
    """演示VLM学科分类"""
    print("\n" + "="*60)
    print("🖼️  VLM 学科分类演示")
    print("="*60)
    
    # 模拟文本分类（实际使用时传入图片bytes）
    test_cases = [
        ("求解方程 x^2 + 3x + 2 = 0", "math"),
        ("计算物体自由落体的速度", "physics"),
        ("H2O的化学性质是什么？", "chemistry"),
        ("细胞的结构包括哪些部分？", "biology"),
    ]
    
    for text, expected in test_cases:
        # 使用关键词降级（实际环境可以用VLM）
        subject, confidence = vlm_service._keyword_classify(text)
        status = "✅" if subject == expected else "⚠️"
        print(f"{status} 文本: {text[:30]}...")
        print(f"   预测: {subject} (置信度: {confidence:.2f}), 期望: {expected}")


async def demo_embedding():
    """演示BGE向量编码"""
    print("\n" + "="*60)
    print("🔢 BGE 向量编码演示")
    print("="*60)
    
    texts = [
        "一元二次方程求根公式",
        "牛顿第二定律的内容",
        "水的化学式是H2O"
    ]
    
    for text in texts:
        vectors = await encode_text(text)
        vector = vectors[0]
        print(f"✅ '{text}'")
        print(f"   向量维度: {len(vector)}")
        print(f"   前5维: {vector[:5]}")
        print(f"   向量模长: {sum(x*x for x in vector)**0.5:.4f}")


async def demo_quality_check():
    """演示云端质检"""
    print("\n" + "="*60)
    print("☁️  云端质检演示 (使用本地规则fallback)")
    print("="*60)
    
    checker = CloudQualityChecker()
    
    test_cases = [
        ("什么是勾股定理？", "直角三角形两直角边的平方和等于斜边的平方，即a² + b² = c²。"),
        ("解释牛顿第一定律", "一切物体在没有受到外力作用时，总保持静止或匀速直线运动状态。"),
    ]
    
    for question, answer in test_cases:
        # 识别知识类型
        k_type = checker.identify_knowledge_type(question, answer)
        print(f"\n📝 问题: {question}")
        print(f"   答案: {answer[:50]}...")
        print(f"   识别类型: {k_type.value}")
        
        # 本地规则评分（API需要真实key）
        scores = checker._local_quality_score(question, answer, k_type)
        overall = checker._calculate_weighted_score(scores, k_type)
        print(f"   质量评分: {overall:.1f}/5.0")
        print(f"   各维度: {scores}")


async def main():
    """主函数"""
    print("🎓 EduQA V2 新功能演示")
    print("="*60)
    
    await demo_vlm_classification()
    await demo_embedding()
    await demo_quality_check()
    
    print("\n" + "="*60)
    print("✅ 所有演示完成！")
    print("="*60)
    print("\n📚 使用说明:")
    print("   1. VLM分类: 调用 vlm_service.classify_image()")
    print("   2. RAG检索: 调用 retriever.retrieve()")
    print("   3. 云端质检: 调用 checker.check_quality()")
    print("   4. 自动入库: 调用 checker.process_interaction()")


if __name__ == "__main__":
    asyncio.run(main())
