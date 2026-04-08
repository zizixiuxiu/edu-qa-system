"""知识库仓储实现"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.models.knowledge import (
    KnowledgeItem, 
    KnowledgeMetadata, 
    KnowledgeTier, 
    KnowledgeType,
    QualityScores,
    RetrievalResult
)
from ....domain.base.repository import Repository
from ..models import KnowledgeDB


class KnowledgeRepository(Repository[KnowledgeItem, int]):
    """知识库仓储"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_domain(self, db_model: KnowledgeDB) -> KnowledgeItem:
        """转换为领域模型"""
        # 构建元数据
        meta_data = db_model.meta_data or {}
        metadata = KnowledgeMetadata(
            question=meta_data.get("question", ""),
            answer=meta_data.get("answer", ""),
            local_answer=meta_data.get("local_answer"),
            knowledge_type=KnowledgeType(meta_data.get("knowledge_type", "qa")),
            source_session_id=meta_data.get("source_session_id"),
            improvement_suggestions=meta_data.get("improvement_suggestions"),
        )
        
        # 构建质量评分
        quality = QualityScores(
            overall=db_model.quality_score,
            accuracy=db_model.accuracy_score,
            completeness=db_model.completeness_score,
            educational=db_model.educational_score,
        )
        
        item = KnowledgeItem(
            expert_id=db_model.expert_id,
            content=db_model.content,
            embedding=db_model.embedding,
            metadata=metadata,
            tier=KnowledgeTier(db_model.tier),
            quality=quality,
            dedup_hash=db_model.dedup_hash,
        )
        
        # 设置基类属性
        item.id = db_model.id
        item.usage_count = db_model.usage_count
        item.created_at = db_model.created_at
        item.updated_at = db_model.updated_at
        
        return item
    
    def _to_db(self, entity: KnowledgeItem) -> KnowledgeDB:
        """转换为数据库模型"""
        return KnowledgeDB(
            id=entity.id,
            expert_id=entity.expert_id,
            content=entity.content,
            embedding=entity.embedding,
            meta_data=entity.metadata.to_dict() if entity.metadata else None,
            tier=entity.tier.value,
            knowledge_type=entity.metadata.knowledge_type.value if entity.metadata else "qa",
            quality_score=entity.quality.overall if entity.quality else 0,
            accuracy_score=entity.quality.accuracy if entity.quality else None,
            completeness_score=entity.quality.completeness if entity.quality else None,
            educational_score=entity.quality.educational if entity.quality else None,
            dedup_hash=entity.dedup_hash,
            usage_count=entity.usage_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    async def get_by_id(self, id: int) -> Optional[KnowledgeItem]:
        result = await self.session.execute(
            select(KnowledgeDB).where(KnowledgeDB.id == id)
        )
        db_model = result.scalar_one_or_none()
        return self._to_domain(db_model) if db_model else None
    
    async def get_all(self) -> List[KnowledgeItem]:
        result = await self.session.execute(select(KnowledgeDB))
        return [self._to_domain(m) for m in result.scalars().all()]
    
    async def get_by_expert(self, expert_id: int) -> List[KnowledgeItem]:
        """根据专家ID获取知识"""
        result = await self.session.execute(
            select(KnowledgeDB).where(KnowledgeDB.expert_id == expert_id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]
    
    async def search_by_content(self, keyword: str, limit: int = 10) -> List[KnowledgeItem]:
        """根据内容关键词搜索"""
        result = await self.session.execute(
            select(KnowledgeDB)
            .where(KnowledgeDB.content.contains(keyword))
            .limit(limit)
        )
        return [self._to_domain(m) for m in result.scalars().all()]
    
    async def add(self, entity: KnowledgeItem) -> KnowledgeItem:
        db_model = self._to_db(entity)
        db_model.id = None
        self.session.add(db_model)
        await self.session.flush()
        await self.session.refresh(db_model)
        entity.id = db_model.id
        return entity
    
    async def update(self, entity: KnowledgeItem) -> KnowledgeItem:
        result = await self.session.execute(
            select(KnowledgeDB).where(KnowledgeDB.id == entity.id)
        )
        db_model = result.scalar_one()
        
        db_model.content = entity.content
        db_model.embedding = entity.embedding
        db_model.meta_data = entity.metadata.to_dict() if entity.metadata else None
        db_model.tier = entity.tier.value
        db_model.quality_score = entity.quality.overall if entity.quality else 0
        db_model.accuracy_score = entity.quality.accuracy if entity.quality else None
        db_model.completeness_score = entity.quality.completeness if entity.quality else None
        db_model.educational_score = entity.quality.educational if entity.quality else None
        db_model.usage_count = entity.usage_count
        db_model.updated_at = entity.updated_at
        
        return entity
    
    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            select(KnowledgeDB).where(KnowledgeDB.id == id)
        )
        db_model = result.scalar_one_or_none()
        if db_model:
            await self.session.delete(db_model)
            return True
        return False
    
    async def exists(self, id: int) -> bool:
        result = await self.session.execute(
            select(KnowledgeDB.id).where(KnowledgeDB.id == id)
        )
        return result.scalar_one_or_none() is not None
    
    async def search_by_vector(
        self,
        embedding: List[float],
        expert_id: Optional[int] = None,
        tier: Optional[int] = None,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        向量相似度检索
        
        Args:
            embedding: 查询向量 (384维)
            expert_id: 专家ID过滤
            tier: 知识层级过滤
            top_k: 返回数量
            threshold: 相似度阈值
        
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        import numpy as np
        from pgvector.sqlalchemy import cosine_distance
        
        # 构建查询：按余弦距离排序
        query = (
            select(KnowledgeDB)
            .order_by(cosine_distance(KnowledgeDB.embedding, embedding))
            .limit(top_k * 2)  # 多取一些用于阈值过滤
        )
        
        # 添加过滤条件
        if expert_id is not None:
            query = query.where(KnowledgeDB.expert_id == expert_id)
        if tier is not None:
            query = query.where(KnowledgeDB.tier == tier)
        
        result = await self.session.execute(query)
        db_models = result.scalars().all()
        
        # 转换为RetrievalResult并计算相似度
        results = []
        query_vec = np.array(embedding)
        query_norm = np.linalg.norm(query_vec)
        
        for rank, db_model in enumerate(db_models, 1):
            if db_model.embedding is None:
                continue
                
            # 计算余弦相似度
            doc_vec = np.array(db_model.embedding)
            doc_norm = np.linalg.norm(doc_vec)
            
            if doc_norm == 0 or query_norm == 0:
                continue
                
            similarity = np.dot(query_vec, doc_vec) / (query_norm * doc_norm)
            
            # 阈值过滤
            if similarity >= threshold:
                item = self._to_domain(db_model)
                results.append(RetrievalResult(
                    knowledge=item,
                    similarity=float(similarity),
                    rank=rank
                ))
        
        # 按相似度排序并限制数量
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
    async def find_duplicate(
        self,
        embedding: List[float],
        threshold: float = 0.92
    ) -> Optional[KnowledgeItem]:
        """
        查找相似知识（用于去重）
        
        Args:
            embedding: 待检查知识的向量
            threshold: 相似度阈值（默认0.92）
        
        Returns:
            Optional[KnowledgeItem]: 如果找到相似知识则返回
        """
        results = await self.search_by_vector(
            embedding=embedding,
            top_k=1,
            threshold=threshold
        )
        return results[0].knowledge if results else None
