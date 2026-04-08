"""RAG 检索服务 - 三级知识库检索"""
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import numpy as np
from ...core.config import get_settings
from ...core.logging import LoggerMixin

settings = get_settings()


@dataclass
class RetrievalResult:
    """检索结果"""
    knowledge_id: int
    content: str
    tier: str  # tier0/tier1/tier2
    similarity: float
    source: str
    quality_score: float


class MultiTierRetriever(LoggerMixin):
    """
    三级RAG检索器
    
    Tier 0: 本地迭代知识库 (High Quality) - 权重 0.95
    Tier 1: 学科专属知识库 (Domain Specific) - 权重 1.0  
    Tier 2: 通用知识库 (Fallback) - 权重 0.7
    
    运行时权重: [0.95, 1.0, 0.7]
    实验权重: [0.5, 0.3, 0.2]
    """
    
    # 运行时权重
    RUNTIME_WEIGHTS = {
        "tier0": 0.95,
        "tier1": 1.0,
        "tier2": 0.7
    }
    
    # 实验分析权重
    EXPERIMENT_WEIGHTS = {
        "tier0": 0.5,
        "tier1": 0.3,
        "tier2": 0.2
    }
    
    # 相似度阈值
    SIMILARITY_THRESHOLD = settings.RAG_SIMILARITY_THRESHOLD  # 0.7
    DEDUP_THRESHOLD = settings.KNOWLEDGE_DEDUP_THRESHOLD  # 0.92
    
    def __init__(self):
        self.top_k = settings.RAG_TOP_K  # 默认5
        
    async def retrieve(
        self,
        query: str,
        expert_id: Optional[int] = None,
        top_k: int = None,
        use_weights: bool = True,
        for_experiment: bool = False
    ) -> List[RetrievalResult]:
        """
        执行三级检索
        
        Args:
            query: 查询文本
            expert_id: 可选的专家ID过滤
            top_k: 返回结果数量
            use_weights: 是否应用层级权重
            for_experiment: 是否使用实验权重
            
        Returns:
            检索结果列表
        """
        top_k = top_k or self.top_k
        
        # 1. 编码查询
        from ...infrastructure.embedding.bge_encoder import compute_query_embedding
        query_embedding = await compute_query_embedding(query)
        
        # 2. 并行检索三级知识库
        tier_results = await self._retrieve_all_tiers(query_embedding, expert_id)
        
        # 3. 融合排序
        if use_weights:
            weights = self.EXPERIMENT_WEIGHTS if for_experiment else self.RUNTIME_WEIGHTS
            fused_results = self._weighted_fusion(tier_results, weights, top_k)
        else:
            fused_results = self._simple_merge(tier_results, top_k)
        
        self.logger.info(
            f"RAG检索完成: query_len={len(query)}, "
            f"tier0={len(tier_results['tier0'])}, "
            f"tier1={len(tier_results['tier1'])}, "
            f"tier2={len(tier_results['tier2'])}, "
            f"returned={len(fused_results)}"
        )
        
        return fused_results
    
    async def _retrieve_all_tiers(
        self,
        query_embedding: List[float],
        expert_id: Optional[int] = None
    ) -> Dict[str, List[RetrievalResult]]:
        """检索所有层级的知识库"""
        import asyncio
        
        results = await asyncio.gather(
            self._retrieve_tier("tier0", query_embedding, expert_id),
            self._retrieve_tier("tier1", query_embedding, expert_id),
            self._retrieve_tier("tier2", query_embedding, expert_id),
        )
        
        return {
            "tier0": results[0],
            "tier1": results[1],
            "tier2": results[2]
        }
    
    async def _retrieve_tier(
        self,
        tier: str,
        query_embedding: List[float],
        expert_id: Optional[int] = None,
        limit: int = 20
    ) -> List[RetrievalResult]:
        """
        使用pgvector检索指定层级的知识

        使用余弦相似度: embedding <=> query_embedding
        """
        from sqlalchemy import text
        from ...infrastructure.database.connection import db

        # 将向量转换为pgvector格式
        vector_str = f"[{','.join(map(str, query_embedding))}]"

        # 解析tier数字
        tier_num = 0 if tier == "tier0" else (1 if tier == "tier1" else 2)

        # 构建SQL查询 - 使用原生SQL和字符串插值（向量需要）
        sql = f"""
            SELECT
                k.id,
                k.content,
                k.tier,
                k.meta_data->>'source' as source,
                k.quality_score,
                1 - (k.embedding <=> '{vector_str}'::vector) as similarity
            FROM knowledge_items k
            WHERE k.tier = {tier_num}
              AND 1 - (k.embedding <=> '{vector_str}'::vector) > {self.SIMILARITY_THRESHOLD}
        """

        if expert_id:
            sql += f" AND k.expert_id = {expert_id}"

        sql += f" ORDER BY similarity DESC LIMIT {limit}"

        results = []
        try:
            async with db.session() as session:
                result = await session.execute(text(sql))
                rows = result.fetchall()

                for row in rows:
                    results.append(RetrievalResult(
                        knowledge_id=row.id,
                        content=row.content,
                        tier=f"tier{row.tier}",
                        similarity=float(row.similarity),
                        source=row.source or "unknown",
                        quality_score=float(row.quality_score) if row.quality_score else 0.0
                    ))
        except Exception as e:
            self.logger.error(f"检索{tier}失败: {e}")

        return results
    
    def _weighted_fusion(
        self,
        tier_results: Dict[str, List[RetrievalResult]],
        weights: Dict[str, float],
        top_k: int
    ) -> List[RetrievalResult]:
        """加权融合排序"""
        all_results = []
        
        for tier, results in tier_results.items():
            weight = weights.get(tier, 1.0)
            for r in results:
                # 加权得分 = 相似度 * 层级权重 * 质量分因子
                quality_factor = min(r.quality_score / 5.0, 1.0) if r.quality_score > 0 else 0.5
                r.similarity = r.similarity * weight * quality_factor
                all_results.append(r)
        
        # 去重（基于知识ID）
        seen_ids = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.similarity, reverse=True):
            if r.knowledge_id not in seen_ids:
                seen_ids.add(r.knowledge_id)
                unique_results.append(r)
        
        return unique_results[:top_k]
    
    def _simple_merge(
        self,
        tier_results: Dict[str, List[RetrievalResult]],
        top_k: int
    ) -> List[RetrievalResult]:
        """简单合并（仅按相似度排序）"""
        all_results = []
        for results in tier_results.values():
            all_results.extend(results)
        
        # 去重并排序
        seen_ids = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.similarity, reverse=True):
            if r.knowledge_id not in seen_ids:
                seen_ids.add(r.knowledge_id)
                unique_results.append(r)
        
        return unique_results[:top_k]
    
    async def check_duplicate(
        self,
        content: str,
        threshold: float = None
    ) -> Optional[Tuple[int, float]]:
        """
        检查知识是否重复

        Args:
            content: 知识内容
            threshold: 相似度阈值，默认使用DEDUP_THRESHOLD

        Returns:
            (重复知识ID, 相似度) 或 None
        """
        threshold = threshold or self.DEDUP_THRESHOLD

        from ...infrastructure.embedding.bge_encoder import compute_query_embedding
        from sqlalchemy import text
        from ...infrastructure.database.connection import db

        embedding = await compute_query_embedding(content)
        vector_str = f"[{','.join(map(str, embedding))}]"

        sql = f"""
            SELECT
                k.id,
                1 - (k.embedding <=> '{vector_str}'::vector) as similarity
            FROM knowledge_items k
            WHERE 1 - (k.embedding <=> '{vector_str}'::vector) > {threshold}
            ORDER BY similarity DESC
            LIMIT 1
        """

        try:
            async with db.session() as session:
                result = await session.execute(text(sql))
                row = result.fetchone()

                if row:
                    return (row.id, float(row.similarity))
        except Exception as e:
            self.logger.error(f"去重检查失败: {e}")

        return None


# 全局检索器实例
_retriever = None


def get_retriever() -> MultiTierRetriever:
    """获取全局检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = MultiTierRetriever()
    return _retriever
