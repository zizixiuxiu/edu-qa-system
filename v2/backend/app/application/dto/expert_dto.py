"""专家模块DTO"""
from typing import Optional
from pydantic import BaseModel, Field


class ExpertDTO(BaseModel):
    """专家DTO"""
    id: int
    subject: str
    name: str
    model_type: str
    status: str
    knowledge_count: int
    tier0_count: int
    total_qa_count: int
    accuracy_rate: float
    created_at: str


class UpdateExpertRequest(BaseModel):
    """更新专家请求"""
    name: Optional[str] = None
    prompt_template: Optional[str] = None
    status: Optional[str] = None  # active, inactive, training


class ExpertStatsDTO(BaseModel):
    """专家统计DTO"""
    total_experts: int
    active_experts: int
    total_knowledge: int
    total_qa: int
