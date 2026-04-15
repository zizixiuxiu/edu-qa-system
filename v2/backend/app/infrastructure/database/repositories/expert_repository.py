"""专家仓储实现"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.models.expert import Expert, ExpertStatus, ExpertMetrics
from ....domain.base.repository import Repository
from ..models import ExpertDB


class ExpertRepository(Repository[Expert, int]):
    """专家仓储"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_domain(self, db_model: ExpertDB) -> Expert:
        """转换为领域模型"""
        expert = Expert(
            subject=db_model.subject,
            name=db_model.name,
            model_type=db_model.model_type,
            lora_path=db_model.lora_path,
            prompt_template=db_model.prompt_template,
            status=ExpertStatus(db_model.status),
            metrics=ExpertMetrics(
                knowledge_count=db_model.knowledge_count,
                tier0_count=db_model.tier0_count,
                sft_data_count=db_model.sft_data_count,
                total_qa_count=db_model.total_qa_count,
                avg_response_time_ms=db_model.avg_response_time_ms,
                accuracy_rate=db_model.accuracy_rate,
            ),
        )
        # 设置基类属性
        expert.id = db_model.id
        expert.created_at = db_model.created_at
        expert.updated_at = db_model.updated_at
        return expert
    
    async def get_by_id(self, id: int) -> Optional[Expert]:
        result = await self.session.execute(
            select(ExpertDB).where(ExpertDB.id == id)
        )
        db_model = result.scalar_one_or_none()
        return self._to_domain(db_model) if db_model else None
    
    async def get_by_subject(self, subject: str) -> Optional[Expert]:
        """根据学科获取专家"""
        result = await self.session.execute(
            select(ExpertDB).where(ExpertDB.subject == subject)
        )
        db_model = result.scalar_one_or_none()
        return self._to_domain(db_model) if db_model else None
    
    async def get_all(self) -> List[Expert]:
        result = await self.session.execute(select(ExpertDB))
        return [self._to_domain(m) for m in result.scalars().all()]
    
    async def add(self, entity: Expert) -> Expert:
        db_model = ExpertDB(
            subject=entity.subject,
            name=entity.name,
            model_type=entity.model_type,
            lora_path=entity.lora_path,
            prompt_template=entity.prompt_template,
            status=entity.status.value,
        )
        self.session.add(db_model)
        await self.session.flush()
        await self.session.refresh(db_model)
        entity.id = db_model.id
        return entity
    
    async def update(self, entity: Expert) -> Expert:
        result = await self.session.execute(
            select(ExpertDB).where(ExpertDB.id == entity.id)
        )
        db_model = result.scalar_one()
        
        # 更新所有字段
        db_model.name = entity.name
        db_model.model_type = entity.model_type
        db_model.lora_path = entity.lora_path
        db_model.prompt_template = entity.prompt_template
        db_model.status = entity.status.value
        
        # 更新指标字段
        db_model.knowledge_count = entity.metrics.knowledge_count
        db_model.tier0_count = entity.metrics.tier0_count
        db_model.sft_data_count = entity.metrics.sft_data_count
        db_model.total_qa_count = entity.metrics.total_qa_count
        db_model.avg_response_time_ms = entity.metrics.avg_response_time_ms
        db_model.accuracy_rate = entity.metrics.accuracy_rate
        
        db_model.updated_at = entity.updated_at
        
        return entity
    
    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            select(ExpertDB).where(ExpertDB.id == id)
        )
        db_model = result.scalar_one_or_none()
        if db_model:
            await self.session.delete(db_model)
            return True
        return False
    
    async def exists(self, id: int) -> bool:
        result = await self.session.execute(
            select(ExpertDB.id).where(ExpertDB.id == id)
        )
        return result.scalar_one_or_none() is not None
