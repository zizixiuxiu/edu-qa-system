"""简化的功能演示 - 无需数据库连接"""
import sys
sys.path.insert(0, '.')

from app.infrastructure.llm.vlm_service import VLMService
from app.infrastructure.embedding.bge_encoder import BGEEncoder
from app.application.services.quality_service import CloudQualityChecker
from app.domain.models.knowledge import KnowledgeType


def demo_vlm_keywords():
    """演示关键词分类"""
    print("\n" + "="*60)
    print("🖼️  VLM 关键词分类演示")
    print("="*60)
    
    vlm = VLMService()
    
    test_cases = [
        ("求解方程 x^2 + 3x + 2 = 0", "math"),
        ("计算物体自由落体的速度 v = gt", "physics"),
        ("H2O + CO2 → H2CO3 化学反应", "chemistry"),
        ("细胞核、线粒体的功能", "biology"),
        ("文言文阅读理解的技巧", "chinese"),
        ("英语语法中的时态用法", "english"),
        ("唐朝的历史发展", "history"),
        ("中国的地形地貌特征", "geography"),
        ("马克思主义基本原理", "politics"),
    ]
    
    for text, expected in test_cases:
        subject, confidence = vlm._keyword_classify(text)
        status = "✅" if subject == expected else "⚠️"
        print(f"{status} [{subject:8s}] 置信度:{confidence:.2f} | {text[:40]}...")


def demo_embedding_mock():
    """演示模拟向量编码"""
    print("\n" + "="*60)
    print("🔢 BGE Mock 向量编码演示")
    print("="*60)
    
    encoder = BGEEncoder()
    encoder._model = "mock"  # 强制使用mock模式
    
    texts = [
        "一元二次方程求根公式",
        "牛顿第二定律的内容",
        "水的化学式是H2O"
    ]
    
    vectors = encoder.encode(texts)
    print(f"✅ 编码 {len(texts)} 个文本")
    print(f"   输出维度: {vectors.shape}")
    print(f"   向量1前5维: {vectors[0][:5]}")
    
    # 计算相似度
    sim = encoder.compute_similarity(vectors[0], vectors[1:])
    print(f"   与文本2的相似度: {sim[0]:.4f}")


def demo_knowledge_type():
    """演示知识类型识别"""
    print("\n" + "="*60)
    print("📚 知识类型自动识别演示")
    print("="*60)
    
    checker = CloudQualityChecker()
    
    test_cases = [
        ("什么是勾股定理？", "直角三角形两直角边的平方和等于斜边的平方，即a² + b² = c²。"),
        ("这道题的解题模板是什么？", "首先设未知数x，然后列方程，最后求解验证。"),
        ("如何解一元二次方程？", "第一步：确定a,b,c的值；第二步：计算判别式..."),
        ("细胞是什么？", "细胞是生物体结构和功能的基本单位。"),
    ]
    
    for question, answer in test_cases:
        k_type = checker.identify_knowledge_type(question, answer)
        print(f"✅ [{k_type.value:10s}] Q: {question}")


def main():
    """主函数"""
    print("🎓 EduQA V2 核心功能演示")
    print("="*60)
    
    demo_vlm_keywords()
    demo_embedding_mock()
    demo_knowledge_type()
    
    print("\n" + "="*60)
    print("✅ 演示完成！")
    print("="*60)


if __name__ == "__main__":
    main()
