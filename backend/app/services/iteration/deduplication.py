"""去重服务 - 向量相似度去重"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.config import settings
from app.models.database import Knowledge, SFTData
from app.utils.embedding import embedding_service

# 尝试导入ML库，失败时使用模拟模式
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[警告] ML库未安装，使用模拟模式")


class DeduplicationService:
    """
    去重服务 - 基于向量相似度
    
    核心功能:
    1. 对知识点进行去重检查
    2. 对微调数据进行去重检查
    3. 使用BGE模型计算语义相似度
    """
    
    def _encode(self, text: str) -> list:
        """编码文本为向量 - 使用共享的embedding服务"""
        # 始终使用同一个embedding服务，确保存储和去重时一致
        return embedding_service.encode(text)
    
    async def check_knowledge_duplicate(
        self,
        session: AsyncSession,
        expert_id: int,
        content: str
    ) -> Optional[Knowledge]:
        """
        检查知识点是否重复
        
        Returns:
            如果存在相似度 >= 阈值的知识，返回该知识
            否则返回None
        """
        # 计算内容的向量
        embedding = self._encode(content)
        
        # 查询相似知识
        from sqlalchemy import select
        
        statement = select(Knowledge).where(
            Knowledge.expert_id == expert_id
        ).order_by(
            Knowledge.embedding.cosine_distance(embedding)
        ).limit(1)
        
        result = await session.execute(statement)
        most_similar = result.scalar_one_or_none()
        
        if most_similar is None:
            return None
        
        # 计算相似度
        similarity = self._calculate_similarity(embedding, most_similar.embedding)
        
        if similarity >= settings.DEDUP_THRESHOLD:
            print(f"[Deduplication] 发现重复知识 (相似度: {similarity:.3f})")
            return most_similar
        
        return None
    
    async def check_sft_data_duplicate(
        self,
        session: AsyncSession,
        expert_id: int,
        instruction: str,
        input_text: Optional[str]
    ) -> bool:
        """
        检查微调数据是否重复
        
        Returns:
            True - 存在重复
            False - 不重复
        """
        # 组合instruction和input
        combined = instruction
        if input_text:
            combined += " " + input_text
        
        # 计算向量
        embedding = self._encode(combined)
        
        # 查询相似数据
        from sqlalchemy import select
        
        statement = select(SFTData).where(
            SFTData.expert_id == expert_id
        ).order_by(
            SFTData.id.desc()  # 只检查最近的100条
        ).limit(100)
        
        result = await session.execute(statement)
        recent_data = result.scalars().all()
        
        for data in recent_data:
            data_combined = data.instruction
            if data.input:
                data_combined += " " + data.input
            
            data_embedding = self._encode(data_combined)
            similarity = self._calculate_similarity(embedding, data_embedding)
            
            if similarity >= settings.DEDUP_THRESHOLD:
                print(f"[Deduplication] 发现重复微调数据 (相似度: {similarity:.3f})")
                return True
        
        return False
    

    
    def _calculate_similarity(self, vec1: list, vec2: list) -> float:
        """计算余弦相似度"""
        if not ML_AVAILABLE:
            # 模拟模式 - 简单的点积计算
            dot = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(x * x for x in vec1) ** 0.5
            norm2 = sum(x * x for x in vec2) ** 0.5
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))


# 导入Column用于类型提示
from sqlalchemy import Column

deduplication_service = DeduplicationService()
