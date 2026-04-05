"""
Tier 0 自动入库服务 - 高质量知识自动入库
"""
import hashlib
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.database import Tier0Knowledge, Expert
from app.core.config import settings


class Tier0IngestService:
    """Tier 0 自动入库服务"""
    
    SIMILARITY_THRESHOLD = 0.92  # 向量去重阈值
    QUALITY_THRESHOLD = 4.0      # 质量入库阈值
    
    async def auto_ingest(
        self,
        session: AsyncSession,
        session_id: int,
        question: str,
        local_answer: str,
        cloud_corrected: str,
        quality_result: Dict[str, Any],
        expert_id: int
    ) -> Dict[str, Any]:
        """自动入库到 Tier 0"""
        try:
            # 1. 质量阈值检查
            overall_score = quality_result.get("overall_score", 0)
            if overall_score < self.QUALITY_THRESHOLD:
                return {
                    "status": "rejected",
                    "reason": f"quality_too_low ({overall_score:.2f} < {self.QUALITY_THRESHOLD})"
                }
            
            # 2. 生成embedding
            from app.utils.embedding import embedding_service
            content_for_embedding = f"问题：{question}\n答案：{cloud_corrected[:300]}"
            embedding = embedding_service.encode(content_for_embedding)
            
            # 3. 去重检查
            duplicate_check = await self._check_duplicate(
                session, embedding, question, overall_score
            )
            
            if duplicate_check["is_duplicate"]:
                return {
                    "status": "rejected",
                    "reason": f"duplicate (similarity: {duplicate_check['similarity']:.3f})"
                }
            
            # 4. 生成去重哈希
            dedup_hash = hashlib.md5(question[:100].encode('utf-8')).hexdigest()
            
            # 5. 创建 Tier0Knowledge 记录
            knowledge_type = quality_result.get("knowledge_type", "qa")
            
            knowledge = Tier0Knowledge(
                expert_id=expert_id,
                content=question[:500],
                embedding=embedding.tolist(),
                meta_data={
                    "question": question,
                    "answer": cloud_corrected,
                    "local_answer": local_answer,
                    "knowledge_type": knowledge_type,
                    "source_session_id": session_id,
                    "improvement_suggestions": quality_result.get("improvement_suggestions", "")
                },
                quality_score=overall_score,
                accuracy_score=quality_result.get("accuracy_score"),
                completeness_score=quality_result.get("completeness_score"),
                educational_score=quality_result.get("educational_score"),
                additional_score=quality_result.get("additional_score"),
                dedup_hash=dedup_hash
            )
            
            session.add(knowledge)
            await session.commit()
            await session.refresh(knowledge)
            
            # 6. 更新专家统计
            await self._update_expert_tier0_count(session, expert_id)
            
            print(f"[Tier0] ✅ 成功入库 (ID: {knowledge.id}): {question[:50]}... (质量: {overall_score:.2f})")
            
            return {
                "status": "success",
                "knowledge_id": knowledge.id,
                "reason": None
            }
            
        except Exception as e:
            await session.rollback()
            print(f"[Tier0] ❌ 入库失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "rejected",
                "reason": f"exception: {str(e)}"
            }
    
    async def _check_duplicate(
        self,
        session: AsyncSession,
        new_embedding: np.ndarray,
        question: str,
        new_score: float
    ) -> Dict[str, Any]:
        """两级去重检查"""
        # 第一层：SimHash快速去重
        dedup_hash = hashlib.md5(question[:100].encode('utf-8')).hexdigest()
        
        hash_stmt = select(Tier0Knowledge).where(
            Tier0Knowledge.dedup_hash == dedup_hash
        )
        hash_result = await session.execute(hash_stmt)
        hash_matches = hash_result.scalars().all()
        
        if hash_matches:
            existing = hash_matches[0]
            return {
                "is_duplicate": True,
                "similarity": 1.0,
                "existing_id": existing.id,
                "action": "keep_old"
            }
        
        # 第二层：向量相似度精确去重
        vector_stmt = select(
            Tier0Knowledge,
            (1 - Tier0Knowledge.embedding.cosine_distance(new_embedding.tolist())).label("similarity")
        ).order_by(
            Tier0Knowledge.embedding.cosine_distance(new_embedding.tolist())
        ).limit(1)
        
        vector_result = await session.execute(vector_stmt)
        closest = vector_result.first()
        
        if closest:
            knowledge, similarity = closest
            similarity = float(similarity)
            
            if similarity >= self.SIMILARITY_THRESHOLD:
                if new_score > knowledge.quality_score:
                    await session.delete(knowledge)
                    await session.commit()
                    print(f"[Tier0] 🔄 替换旧记录 (ID: {knowledge.id})")
                    return {
                        "is_duplicate": False,
                        "similarity": similarity,
                        "existing_id": None,
                        "action": "replaced"
                    }
                else:
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "existing_id": knowledge.id,
                        "action": "keep_old"
                    }
        
        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "existing_id": None,
            "action": "new"
        }
    
    async def _update_expert_tier0_count(self, session: AsyncSession, expert_id: int):
        """更新专家的Tier 0知识数量统计"""
        from sqlalchemy import func
        
        count_stmt = select(func.count()).where(
            Tier0Knowledge.expert_id == expert_id
        )
        count_result = await session.execute(count_stmt)
        count = count_result.scalar()
        
        expert = await session.get(Expert, expert_id)
        if expert:
            expert.tier0_count = count
            await session.commit()
            print(f"[Tier0] 📊 更新专家 {expert.subject} 的Tier 0数量: {count}")


# 全局实例
tier0_ingest_service = Tier0IngestService()
