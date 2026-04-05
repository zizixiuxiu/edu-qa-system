"""
RAG检索服务 - 支持知识类型感知的智能检索
策略：
1. 根据查询意图识别需要的知识类型
2. 优先检索对应类型的知识
3. 专家库+通用库的级联检索
4. 按类型和相似度综合排序
"""
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from dataclasses import dataclass
import re

from app.models.database import Knowledge, Expert
from app.utils.embedding import embedding_service
from app.core.config import settings


@dataclass
class RetrievalResult:
    """检索结果"""
    knowledge: Knowledge
    similarity: float
    source: str  # "expert" | "general"
    type_boost: float = 0.0  # 类型匹配增益


class RetrievalService:
    """
    RAG检索服务 - 知识类型感知版
    
    检索策略：
    1. 分析查询意图，识别需要的知识类型
    2. 优先检索匹配类型的知识，给予相似度加成
    3. 专家库优先，相似度不足时触发通用库
    4. 混合排序：综合相似度 + 类型匹配 + 质量分
    """
    
    # 触发通用库检索的阈值
    GENERAL_TRIGGER_THRESHOLD = 0.75
    GENERAL_MIN_THRESHOLD = 0.6
    
    # 类型匹配相似度加成
    TYPE_BOOST = 0.08  # 类型匹配时相似度+0.08
    
    # 查询意图识别关键词
    QUERY_TYPE_PATTERNS = {
        "formula": ["公式", "计算", "等于", "求解", "值", "结果", "多少", "=?", "=?", "怎么算"],
        "concept": ["定义", "概念", "是什么", "什么意思", "含义", "指什么", "什么是"],
        "template": ["模板", "格式", "怎么写", "范文", "例子", "示例", "参考"],
        "step": ["步骤", "怎么做", "如何", "方法", "过程", "流程"],
    }
    
    def __init__(self):
        self.embedding_service = embedding_service
    
    def detect_query_type(self, query: str) -> Optional[str]:
        """
        检测查询需要的知识类型
        
        Returns:
            知识类型或None（混合类型）
        """
        query_lower = query.lower()
        scores = {}
        
        for type_name, patterns in self.QUERY_TYPE_PATTERNS.items():
            score = sum(2 for p in patterns if p in query_lower)
            # 数学公式特殊检测
            if type_name == "formula" and re.search(r'[\d\+\-\*/=\(\)]{3,}', query):
                score += 3
            if score > 0:
                scores[type_name] = score
        
        # 返回得分最高的类型，如果分数差距不明显则返回None（混合检索）
        if scores:
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
            # 如果最高分 >= 第二高分 + 2，才确定为特定类型
            second_best = max((s for t, s in scores.items() if t != best_type), default=0)
            if best_score >= second_best + 2:
                return best_type
        
        return None  # 混合类型，不偏好特定类型
    
    async def retrieve(
        self,
        session: AsyncSession,
        expert_id: int,
        query: str,
        top_k: int = 5,
        max_general: int = 3
    ) -> Tuple[List[RetrievalResult], Dict]:
        """
        智能检索知识
        
        Args:
            session: 数据库会话
            expert_id: 专家ID
            query: 查询文本
            top_k: 返回结果数量
            max_general: 最多返回的通用知识数量
            
        Returns:
            (结果列表, 检索统计信息)
        """
        # 1. 检测查询类型
        query_type = self.detect_query_type(query)
        
        # 2. 向量化查询
        query_embedding = self.embedding_service.encode(query)
        
        results = []
        stats = {
            "query_type": query_type,
            "expert_searched": False,
            "general_searched": False,
            "expert_max_similarity": 0.0,
            "general_max_similarity": 0.0,
            "type_distribution": {},
            "trigger_reason": None
        }
        
        # 3. 检索专家知识库
        expert_results = await self._search_expert_knowledge(
            session, expert_id, query_embedding, top_k * 3, query_type
        )
        stats["expert_searched"] = True
        
        if expert_results:
            max_sim = max(r.similarity + r.type_boost for r in expert_results)
            stats["expert_max_similarity"] = max_sim
            results.extend(expert_results)
        
        # 4. 判断是否触发通用库检索
        should_trigger_general = self._should_trigger_general(
            expert_results, self.GENERAL_TRIGGER_THRESHOLD
        )
        
        if should_trigger_general:
            stats["trigger_reason"] = f"专家库最高相似度({stats['expert_max_similarity']:.3f})低于阈值"
            
            general_expert = await self._get_general_expert(session)
            
            if general_expert and general_expert.id != expert_id:
                general_results = await self._search_expert_knowledge(
                    session, 
                    general_expert.id, 
                    query_embedding, 
                    top_k * 2,
                    query_type,
                    min_threshold=self.GENERAL_MIN_THRESHOLD
                )
                
                stats["general_searched"] = True
                if general_results:
                    stats["general_max_similarity"] = max(
                        r.similarity + r.type_boost for r in general_results
                    )
                    
                    for r in general_results:
                        r.source = "general"
                    
                    results.extend(general_results)
        else:
            stats["trigger_reason"] = f"专家库相似度充足({stats['expert_max_similarity']:.3f})"
        
        # 5. 综合排序（相似度 + 类型加成 + 质量分）
        unique_results = self._rank_results(results, query_type)
        
        # 6. 限制来源比例
        final_results = self._balance_sources(unique_results, top_k, max_general)
        
        # 7. 更新统计
        stats["total_results"] = len(final_results)
        stats["expert_results"] = sum(1 for r in final_results if r.source == "expert")
        stats["general_results"] = sum(1 for r in final_results if r.source == "general")
        stats["type_distribution"] = self._count_types(final_results)
        
        return final_results, stats
    
    async def _search_expert_knowledge(
        self,
        session: AsyncSession,
        expert_id: int,
        query_embedding: List[float],
        limit: int,
        query_type: Optional[str] = None,
        min_threshold: float = 0.5
    ) -> List[RetrievalResult]:
        """
        搜索专家知识库（支持类型过滤）
        
        如果query_type不为None，优先检索该类型，但仍返回其他类型
        """
        # 基础查询
        base_query = select(
            Knowledge,
            Knowledge.embedding.cosine_distance(query_embedding).label("distance")
        ).where(
            Knowledge.expert_id == expert_id
        )
        
        # 如果指定了查询类型，优先检索该类型（多取一些）
        if query_type:
            # 先查匹配类型的
            type_query = base_query.where(
                Knowledge.knowledge_type == query_type
            ).order_by("distance").limit(limit)
            
            result = await session.execute(type_query)
            type_rows = result.all()
            
            # 如果匹配类型的不够，再查其他类型
            if len(type_rows) < limit // 2:
                other_query = base_query.where(
                    Knowledge.knowledge_type != query_type
                ).order_by("distance").limit(limit - len(type_rows))
                
                result = await session.execute(other_query)
                other_rows = result.all()
                rows = type_rows + other_rows
            else:
                rows = type_rows
        else:
            # 未指定类型，全部检索
            statement = base_query.order_by("distance").limit(limit)
            result = await session.execute(statement)
            rows = result.all()
        
        results = []
        for knowledge, distance in rows:
            similarity = 1.0 - float(distance)
            
            # 计算类型加成
            type_boost = 0.0
            if query_type and knowledge.knowledge_type == query_type:
                type_boost = self.TYPE_BOOST
            
            # 质量分加权（质量分0-5，转换为0-0.05的加成）
            quality_boost = knowledge.quality_score * 0.01
            
            if similarity >= min_threshold:
                results.append(RetrievalResult(
                    knowledge=knowledge,
                    similarity=similarity,
                    source="expert",
                    type_boost=type_boost + quality_boost
                ))
        
        return results
    
    def _rank_results(
        self,
        results: List[RetrievalResult],
        query_type: Optional[str]
    ) -> List[RetrievalResult]:
        """
        综合排序结果
        
        排序依据：
        1. 综合得分 = 相似度 + 类型加成 + 质量加成
        2. 去重（相同内容保留得分最高的）
        """
        # 计算综合得分
        for r in results:
            r.combined_score = r.similarity + r.type_boost
        
        # 按内容去重
        seen_content = {}
        for result in results:
            content = result.knowledge.content.strip()
            if content not in seen_content or seen_content[content].combined_score < result.combined_score:
                seen_content[content] = result
        
        # 按综合得分排序
        unique_results = list(seen_content.values())
        unique_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        return unique_results
    
    async def _get_general_expert(self, session: AsyncSession) -> Optional[Expert]:
        """获取通用专家"""
        statement = select(Expert).where(
            or_(
                Expert.subject == "通用",
                Expert.subject == "其他"
            )
        ).limit(1)
        result = await session.execute(statement)
        return result.scalar_one_or_none()
    
    def _should_trigger_general(
        self, 
        expert_results: List[RetrievalResult], 
        threshold: float
    ) -> bool:
        """判断是否触发通用库检索"""
        if not expert_results:
            return True
        
        max_combined = max(r.similarity + r.type_boost for r in expert_results)
        return max_combined < threshold
    
    def _balance_sources(
        self,
        results: List[RetrievalResult],
        top_k: int,
        max_general: int
    ) -> List[RetrievalResult]:
        """平衡来源比例"""
        expert_results = [r for r in results if r.source == "expert"]
        general_results = [r for r in results if r.source == "general"]
        
        final_results = expert_results[:top_k]
        
        if len(final_results) < top_k:
            remaining = top_k - len(final_results)
            general_to_add = min(remaining, max_general, len(general_results))
            final_results.extend(general_results[:general_to_add])
        
        return final_results
    
    def _count_types(self, results: List[RetrievalResult]) -> Dict[str, int]:
        """统计结果中的类型分布"""
        distribution = {}
        for r in results:
            ktype = r.knowledge.knowledge_type
            distribution[ktype] = distribution.get(ktype, 0) + 1
        return distribution


# 全局服务实例
retrieval_service = RetrievalService()
