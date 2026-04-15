"""
多级检索服务 - 学科库优先，通用库兜底
整合处理好的数据集（18万条）
"""
import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import pickle

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import func

# 延迟导入embedding服务
embedding_service = None

def get_embedding_service():
    global embedding_service
    if embedding_service is None:
        from app.utils.embedding import embedding_service as es
        embedding_service = es
    return embedding_service


@dataclass
class RetrievalResult:
    """检索结果"""
    id: str
    question: str
    answer: str
    subject: str
    dataset: str
    type: str  # choice / open
    score: float
    tier: int  # 0: Tier 0本地高质量库, 1: 学科库, 2: 通用库
    metadata: Dict


class VectorStore:
    """向量存储 - 内存版"""
    
    def __init__(self, name: str):
        self.name = name
        self.docs: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_dim = 384
    
    def add_documents(self, documents: List[Dict]):
        """添加文档"""
        if not documents:
            return
        
        start_idx = len(self.docs)
        self.docs.extend(documents)
        
        # 编码
        es = get_embedding_service()
        contents = [doc['content'] for doc in documents]
        embeddings = es.encode_batch(contents)
        
        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])
        
        print(f"    [{self.name}] 添加 {len(documents)} 个文档，总计 {len(self.docs)} 个")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """向量搜索"""
        if not self.docs or self.embeddings is None:
            return []
        
        # 余弦相似度
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-8
        )
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(int(idx), float(similarities[idx])) for idx in top_indices]
    
    def save(self, cache_dir: str):
        """保存缓存"""
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{self.name}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'docs': self.docs,
                'embeddings': self.embeddings
            }, f)
    
    def load(self, cache_file: str) -> bool:
        """加载缓存"""
        if not os.path.exists(cache_file):
            return False
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        self.docs = data['docs']
        self.embeddings = data['embeddings']
        return True


class MultiTierRetriever:
    """多级检索器"""
    
    SUBJECT_MAPPING = {
        '数学': 'math', '物理': 'physics', '化学': 'chemistry',
        '生物': 'biology', '地理': 'geography', '历史': 'history',
        '语文': 'chinese', '英语': 'english',
        '通用': 'general', '综合': 'general'
    }
    
    def __init__(self, data_dir: str = "D:/毕设数据集/processed"):
        self.data_dir = data_dir
        self.cache_dir = "D:/毕设数据集/vector_cache_v2"
        
        self.subject_stores: Dict[str, VectorStore] = {}
        self.general_store = VectorStore("general")
        
        self._load_data()
    
    def _load_data(self):
        """加载数据集"""
        print("📚 初始化多级检索...")
        
        # 检查缓存
        cache_meta = os.path.join(self.cache_dir, "meta.json")
        if os.path.exists(cache_meta):
            print("  从缓存加载...")
            self._load_from_cache()
            return
        
        # 从文件加载
        print("  从数据文件构建...")
        total_docs = 0
        for subject_dir in Path(self.data_dir).iterdir():
            if not subject_dir.is_dir():
                continue
            
            subject = subject_dir.name
            documents = self._load_subject_docs(subject_dir)
            
            if not documents:
                continue
            
            total_docs += len(documents)
            
            if subject in ['通用', '综合']:
                print(f"  📦 通用知识: {len(documents)} 条")
                self.general_store.add_documents(documents)
            else:
                print(f"  📖 {subject}: {len(documents)} 条")
                store = VectorStore(subject)
                store.add_documents(documents)
                self.subject_stores[subject] = store
        
        # 保存缓存
        self._save_cache()
        print(f"✅ 加载完成: {len(self.subject_stores)} 个学科库 + 通用库，总计 {total_docs} 条")
    
    def _load_subject_docs(self, subject_dir: Path) -> List[Dict]:
        """加载学科文档"""
        documents = []
        
        for jsonl_file in subject_dir.glob("*.jsonl"):
            if jsonl_file.name == 'statistics.json':
                continue
            
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        
                        # 构建向量化内容 - 只包含问题，不含答案！
                        question = item.get('question', '')
                        content = f"问题: {question}"
                        
                        documents.append({
                            'id': item.get('id', ''),
                            'content': content,
                            'question': question,
                            'answer': item.get('answer', ''),
                            'subject': item.get('subject', subject_dir.name),
                            'dataset': item.get('dataset', ''),
                            'type': item.get('type', 'unknown'),
                            'metadata': item
                        })
                    except:
                        continue
        
        return documents
    
    def _load_from_cache(self):
        """从缓存加载"""
        # 加载通用库
        general_cache = os.path.join(self.cache_dir, "general.pkl")
        if os.path.exists(general_cache):
            self.general_store.load(general_cache)
        
        # 加载学科库
        for cache_file in Path(self.cache_dir).glob("*.pkl"):
            if cache_file.stem == 'general':
                continue
            subject = cache_file.stem
            store = VectorStore(subject)
            store.load(str(cache_file))
            self.subject_stores[subject] = store
        
        total = sum(len(s.docs) for s in self.subject_stores.values()) + len(self.general_store.docs)
        print(f"✅ 从缓存加载: {len(self.subject_stores)} 个学科库，总计 {total} 条")
    
    def _save_cache(self):
        """保存缓存"""
        print("💾 保存向量缓存...")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.general_store.save(self.cache_dir)
        for subject, store in self.subject_stores.items():
            store.save(self.cache_dir)
        
        # 保存元数据
        meta = {
            'subjects': list(self.subject_stores.keys()),
            'general_count': len(self.general_store.docs),
        }
        with open(os.path.join(self.cache_dir, "meta.json"), 'w', encoding='utf-8') as f:
            json.dump(meta, f)
        print(f"  缓存已保存到: {self.cache_dir}")
    
    async def retrieve(
        self,
        session: AsyncSession,  # 新增
        query: str,
        subject: Optional[str] = None,
        top_k: int = 5,
        tier_weights: Tuple[float, float, float] = (0.95, 1.0, 0.7),  # Tier 0/1/2
        score_threshold: float = 0.5
    ) -> List[RetrievalResult]:
        """三级检索 - Tier 0 > Tier 1 > Tier 2"""
        from app.utils.embedding import embedding_service
        query_embedding = embedding_service.encode(query)
        
        all_results = []
        
        # T0: Tier 0 本地高质量知识库（新增）
        if subject:
            t0_results = await self._search_tier0(
                session, query_embedding, subject, top_k=top_k
            )
            for knowledge, score in t0_results:
                weighted_score = score * tier_weights[0]
                all_results.append((knowledge, weighted_score, 0))
        
        # T1: 学科库检索（现有代码保留）
        if subject and subject in self.subject_stores:
            store = self.subject_stores[subject]
            search_results = store.search(query_embedding, top_k=top_k * 2)
            
            for idx, score in search_results:
                doc = store.docs[idx]
                weighted_score = score * tier_weights[1]
                all_results.append((doc, weighted_score, 1))
        
        # T2: 通用库检索（现有代码保留）
        need_t2 = not all_results or all_results[0][1] < score_threshold
        if need_t2 and len(self.general_store.docs) > 0:
            search_results = self.general_store.search(query_embedding, top_k=top_k)
            
            for idx, score in search_results:
                doc = self.general_store.docs[idx]
                weighted_score = score * tier_weights[2]
                
                # 去重检查
                doc_id = doc.get('id', '')
                if not any(
                    (isinstance(r[0], dict) and r[0].get('id') == doc_id) or
                    (hasattr(r[0], 'id') and r[0].id == doc_id)
                    for r in all_results
                ):
                    all_results.append((doc, weighted_score, 2))
        
        # 排序并取 top_k
        all_results.sort(key=lambda x: x[1], reverse=True)
        
        # 转换为 RetrievalResult
        results = []
        for item, score, tier in all_results[:top_k]:
            if tier == 0:
                # Tier 0: Tier0Knowledge 对象
                results.append(RetrievalResult(
                    id=f"t0_{item.id}",
                    question=item.meta_data.get('question', item.content),
                    answer=item.meta_data.get('answer', ''),
                    subject=subject or '通用',
                    dataset='tier0_local',
                    type=item.meta_data.get('knowledge_type', 'qa'),
                    score=score,
                    tier=tier,
                    metadata={
                        'quality_score': item.quality_score,
                        'accuracy_score': item.accuracy_score,
                        'source': 'tier0_local'
                    }
                ))
            else:
                # Tier 1/2: dict 格式
                results.append(RetrievalResult(
                    id=item['id'],
                    question=item['question'],
                    answer=item['answer'],
                    subject=item['subject'],
                    dataset=item['dataset'],
                    type=item['type'],
                    score=score,
                    tier=tier,
                    metadata=item.get('metadata', {})
                ))
        
        return results
    
    def format_context(self, results: List[RetrievalResult]) -> str:
        """格式化检索结果"""
        if not results:
            return ""
        
        contexts = []
        for i, r in enumerate(results, 1):
            tier_label = {0: "[高质量]", 1: "[学科库]", 2: "[通用库]"}.get(r.tier, "")
            
            ctx = f"{tier_label}[{i}] {r.question}"
            
            if r.tier == 0 and r.metadata.get('quality_score'):
                ctx += f" (质量分: {r.metadata['quality_score']:.1f})"
            
            if r.type == 'choice' and r.metadata.get('choices'):
                choices = r.metadata['choices'][:4]
                ctx += f"\n选项: {', '.join(str(c) for c in choices)}"
            
            contexts.append(ctx)
        
        return "\n\n".join(contexts)
    
    async def _search_tier0(
        self,
        session: AsyncSession,
        query_embedding: np.ndarray,
        subject: str,
        top_k: int = 3
    ) -> List[Tuple[Any, float]]:
        """搜索 Tier 0 本地高质量知识库"""
        from app.models.database import Tier0Knowledge, Expert
        
        # 获取专家ID
        expert_stmt = select(Expert).where(Expert.subject == subject)
        expert_result = await session.execute(expert_stmt)
        expert = expert_result.scalar_one_or_none()
        
        if not expert:
            return []
        
        # 使用 PostgreSQL 向量操作符 <=> (余弦距离)
        # 余弦相似度 = 1 - 余弦距离
        stmt = select(
            Tier0Knowledge,
            (1 - func.cosine_distance(Tier0Knowledge.embedding, query_embedding.tolist())).label("similarity")
        ).where(
            Tier0Knowledge.expert_id == expert.id
        ).order_by(
            Tier0Knowledge.embedding.op('<=>')(query_embedding.tolist())
        ).limit(top_k)
        
        result = await session.execute(stmt)
        return [(row[0], float(row[1])) for row in result.all() if row[1] is not None]


# 全局单例
multi_tier_retriever = None

def get_retriever():
    global multi_tier_retriever
    if multi_tier_retriever is None:
        multi_tier_retriever = MultiTierRetriever()
    return multi_tier_retriever
