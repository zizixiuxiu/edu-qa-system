"""知识检索服务"""
from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.knowledge import KnowledgeItem, RetrievalResult
from ...core.logging import LoggerMixin


class EmbeddingService(ABC):
    """Embedding服务接口"""
    
    @abstractmethod
    async def encode(self, text: str) -> List[float]:
        """文本向量化"""
        pass
    
    @abstractmethod
    async def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算相似度"""
        pass


class KnowledgeRepository(ABC):
    """知识仓储接口"""
    
    @abstractmethod
    async def search_by_vector(
        self,
        embedding: List[float],
        expert_id: Optional[int] = None,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """向量检索"""
        pass


class RetrievalService(LoggerMixin):
    """知识检索服务"""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        knowledge_repo: KnowledgeRepository
    ):
        self.embedding_service = embedding_service
        self.knowledge_repo = knowledge_repo
    
    async def retrieve(
        self,
        query: str,
        expert_id: Optional[int] = None,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            expert_id: 专家ID（可选，用于专家库过滤）
            top_k: 返回数量
            threshold: 相似度阈值
        
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        try:
            # 1. 向量化查询
            query_embedding = await self.embedding_service.encode(query)
            
            # 2. 向量检索
            results = await self.knowledge_repo.search_by_vector(
                embedding=query_embedding,
                expert_id=expert_id,
                top_k=top_k,
                threshold=threshold
            )
            
            self.logger.info(
                "Knowledge retrieved",
                query_preview=query[:50],
                expert_id=expert_id,
                result_count=len(results),
                top_similarity=results[0].similarity if results else 0
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Retrieval failed", error=str(e), query=query[:50])
            return []
    
    async def retrieve_for_rag(
        self,
        query: str,
        expert_id: Optional[int] = None,
        top_k: int = 5
    ) -> str:
        """
        检索并格式化为RAG上下文
        
        Returns:
            str: 格式化的上下文文本
        """
        results = await self.retrieve(query, expert_id, top_k)
        
        if not results:
            return "暂无相关知识。"
        
        contexts = []
        for i, result in enumerate(results, 1):
            knowledge = result.knowledge
            contexts.append(
                f"[{i}] 相似度: {result.similarity:.2f}\n"
                f"问题: {knowledge.metadata.question}\n"
                f"答案: {knowledge.metadata.answer}\n"
            )
        
        return "\n".join(contexts)
    
    def format_retrieval_results(self, results: List[RetrievalResult]) -> List[dict]:
        """格式化检索结果为字典列表"""
        return [
            {
                "knowledge_id": r.knowledge.id,
                "similarity": r.similarity,
                "rank": r.rank,
                "question": r.knowledge.metadata.question,
                "answer": r.knowledge.metadata.answer[:200] + "...",
            }
            for r in results
        ]
