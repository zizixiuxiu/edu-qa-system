"""专家应用服务"""
import asyncio
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logging import LoggerMixin
from ...core.exceptions import ResourceNotFoundError
from ...domain.models.expert import Expert, ExpertStatus, ExpertMetrics
from ...infrastructure.database.repositories.expert_repository import ExpertRepository


class ExpertApplicationService(LoggerMixin):
    """专家应用服务 - 实现四级缓存架构中的L1内存缓存"""
    
    # L1 内存缓存 (类级别，所有实例共享)
    _cache: Dict[str, Expert] = {}
    _cache_by_id: Dict[int, Expert] = {}
    _cache_lock = asyncio.Lock()
    
    def __init__(self, session: AsyncSession):
        self.repo = ExpertRepository(session)
    
    def _get_from_cache(self, subject: str) -> Optional[Expert]:
        """从L1缓存获取专家 (O(1)时间复杂度)"""
        return self._cache.get(subject)
    
    def _get_from_cache_by_id(self, expert_id: int) -> Optional[Expert]:
        """从L1缓存通过ID获取专家 (O(1)时间复杂度)"""
        return self._cache_by_id.get(expert_id)
    
    async def _update_cache(self, expert: Expert) -> None:
        """更新L1缓存"""
        async with self._cache_lock:
            self._cache[expert.subject] = expert
            if expert.id:
                self._cache_by_id[expert.id] = expert
    
    async def _invalidate_cache(self, subject: Optional[str] = None, expert_id: Optional[int] = None) -> None:
        """使缓存失效"""
        async with self._cache_lock:
            if subject and subject in self._cache:
                expert = self._cache.pop(subject)
                if expert.id and expert.id in self._cache_by_id:
                    del self._cache_by_id[expert.id]
            elif expert_id and expert_id in self._cache_by_id:
                expert = self._cache_by_id.pop(expert_id)
                if expert.subject in self._cache:
                    del self._cache[expert.subject]
    
    async def get_all_experts(self) -> List[dict]:
        """获取所有专家"""
        experts = await self.repo.get_all()
        return [e.to_dict() for e in experts]
    
    async def get_expert_by_id(self, expert_id: int) -> dict:
        """根据ID获取专家 - 带L1缓存"""
        # L1缓存检查 (< 1ms)
        cached = self._get_from_cache_by_id(expert_id)
        if cached:
            self.logger.debug(f"L1 cache hit for expert_id: {expert_id}")
            return cached.to_dict()
        
        # L3数据库查询 (~ 10-50ms)
        expert = await self.repo.get_by_id(expert_id)
        if not expert:
            raise ResourceNotFoundError(f"Expert not found: {expert_id}")
        
        # 写入L1缓存
        await self._update_cache(expert)
        return expert.to_dict()
    
    async def get_expert_by_subject(self, subject: str) -> dict:
        """根据学科获取专家 - 带L1缓存"""
        # L1缓存检查 (< 1ms)
        cached = self._get_from_cache(subject)
        if cached:
            self.logger.debug(f"L1 cache hit for subject: {subject}")
            return cached.to_dict()
        
        # L3数据库查询 (~ 10-50ms)
        expert = await self.repo.get_by_subject(subject)
        if not expert:
            raise ResourceNotFoundError(f"Expert not found: {subject}")
        
        # 写入L1缓存
        await self._update_cache(expert)
        return expert.to_dict()
    
    async def update_expert(
        self,
        expert_id: int,
        name: str = None,
        prompt_template: str = None,
        status: str = None
    ) -> dict:
        """更新专家 - 带缓存失效"""
        expert = await self.repo.get_by_id(expert_id)
        if not expert:
            raise ResourceNotFoundError(f"Expert not found: {expert_id}")
        
        if name:
            expert.name = name
        if prompt_template:
            expert.prompt_template = prompt_template
        if status:
            expert.status = ExpertStatus(status)
        
        expert.update_timestamp()
        updated = await self.repo.update(expert)
        
        # 使缓存失效并更新
        await self._invalidate_cache(expert_id=expert_id)
        await self._update_cache(updated)
        
        self.logger.info(f"Updated expert: {expert_id}")
        return updated.to_dict()
    
    async def get_subjects(self) -> List[str]:
        """获取所有学科列表"""
        experts = await self.repo.get_all()
        return [e.subject for e in experts]
    
    async def get_stats(self) -> dict:
        """获取专家统计"""
        experts = await self.repo.get_all()
        
        total = len(experts)
        active = sum(1 for e in experts if e.status == ExpertStatus.ACTIVE)
        total_knowledge = sum(e.metrics.knowledge_count for e in experts)
        total_qa = sum(e.metrics.total_qa_count for e in experts)
        
        return {
            "total_experts": total,
            "active_experts": active,
            "total_knowledge": total_knowledge,
            "total_qa": total_qa,
        }
    
    async def ensure_default_experts(self) -> None:
        """确保默认专家存在"""
        default_subjects = [
            "数学", "物理", "化学", "生物",
            "语文", "英语", "历史", "地理", "政治",
            "通用"
        ]
        
        for subject in default_subjects:
            existing = await self.repo.get_by_subject(subject)
            if not existing:
                expert = Expert(
                    subject=subject,
                    name=f"{subject}专家",
                    status=ExpertStatus.ACTIVE,
                )
                await self.repo.add(expert)
                self.logger.info(f"Created default expert: {subject}")
