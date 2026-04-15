"""
预构建向量缓存
首次运行会加载并编码18万条数据，后续启动会更快
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag.multi_tier_retrieval import MultiTierRetriever

def main():
    print("🔨 构建向量缓存")
    print("="*60)
    print("\n这将加载18万条数据并构建向量索引...")
    print("首次运行需要几分钟，请耐心等待\n")
    
    try:
        # 初始化检索器（会自动构建缓存）
        retriever = MultiTierRetriever()
        
        print("\n" + "="*60)
        print("✅ 缓存构建完成！")
        print("="*60)
        
        # 显示统计
        print(f"\n📊 数据统计:")
        print(f"  学科库数量: {len(retriever.subject_stores)}")
        print(f"  通用库文档: {len(retriever.general_store.docs):,}")
        
        for subject, store in retriever.subject_stores.items():
            print(f"  {subject}: {len(store.docs):,} 条")
        
        print(f"\n💾 缓存位置: D:/毕设数据集/vector_cache_v2/")
        
        # 测试检索
        print("\n🧪 测试检索...")
        results = retriever.retrieve("勾股定理是什么？", subject="数学", top_k=3)
        print(f"  检索到 {len(results)} 条结果")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] [{r.tier}] {r.question[:50]}...")
        
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
