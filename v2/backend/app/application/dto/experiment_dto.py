"""实验模块DTO"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExperimentConfigDTO(BaseModel):
    """实验配置DTO"""
    name: str = Field(..., min_length=1)
    description: str = ""
    random_seed: int = Field(default=42)
    use_rag: bool = True
    use_expert_routing: bool = True
    enable_iteration: bool = False
    max_questions: Optional[int] = Field(default=50, ge=1, le=1000)
    subject: Optional[str] = None
    year: Optional[str] = None


class CreateExperimentRequest(BaseModel):
    """创建实验请求"""
    experiments: List[ExperimentConfigDTO]


class CreateExperimentResponse(BaseModel):
    """创建实验响应"""
    success: bool
    experiment_ids: List[str]
    message: str


class ExperimentQueueItemDTO(BaseModel):
    """实验队列项DTO"""
    id: str
    name: str
    status: str  # pending, running, completed
    config: Dict[str, Any]
    progress: int  # 0-100
    current_question: int
    total_questions: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExperimentQueueResponse(BaseModel):
    """实验队列响应"""
    current_id: Optional[str]
    queue: List[ExperimentQueueItemDTO]
    total: int
    pending: int
    running: int
    completed: int


class BenchmarkProgressDTO(BaseModel):
    """基准测试进度DTO"""
    status: str  # idle, running, completed, error
    current: int
    total: int
    current_question: str
    elapsed_time: int


class BenchmarkResultDTO(BaseModel):
    """基准测试结果DTO"""
    experiment_id: str
    total_questions: int
    correct_count: int
    wrong_count: int
    accuracy_rate: float
    avg_score: float
    by_subject: Dict[str, Dict[str, Any]]


class ReportSummaryDTO(BaseModel):
    """报告摘要DTO"""
    filename: str
    test_id: str
    experiment_name: str
    created_at: str
    total_questions: int
    accuracy_rate: float
    avg_score: float
