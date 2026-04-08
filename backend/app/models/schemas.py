"""API数据模型 / Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ========== 通用响应 ==========
class ResponseBase(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


# ========== 专家相关 ==========
class ExpertCreate(BaseModel):
    """创建新学科专家"""
    subject: str          # 学科名称，如"数学"
    name: Optional[str] = None  # 可选自定义名称，默认为"{subject}专家"


class ExpertResponse(BaseModel):
    """专家响应模型 - 按学科划分"""
    id: int
    subject: str          # 学科名称
    name: str             # 显示名称
    knowledge_count: int
    sft_data_count: int
    total_qa_count: int
    avg_response_time: float
    accuracy_rate: float
    is_active: bool
    created_at: datetime


# ========== 问答相关 ==========
class ChatRequest(BaseModel):
    query: str = ""                       # 用户问题（纯图片时可为空）
    image: Optional[str] = None          # base64图片
    session_id: Optional[str] = None     # 续对话


class ChatResponseData(BaseModel):
    answer: str
    session_id: str
    expert_name: str
    expert_subject: str
    used_knowledges: Optional[List[Dict]] = None
    response_time: float
    rag_stats: Optional[Dict] = None  # 检索统计信息（级联检索用）


# ========== 知识库相关 ==========
class KnowledgeCreate(BaseModel):
    content: str
    expert_id: int
    source_type: str = "imported"


class KnowledgeResponse(BaseModel):
    id: int
    expert_id: int
    content: str
    source_type: str
    quality_score: float
    usage_count: int
    created_at: datetime


# ========== 实验控制相关 ==========
class ExperimentMode(str, Enum):
    BASELINE = "baseline"
    RAG_ONLY = "rag_only"
    EXPERT_ROUTING = "expert_routing"
    FULL_SYSTEM = "full_system"
    ABLATION_NO_ITERATION = "ablation_no_iteration"
    ABLATION_NO_FINETUNE = "ablation_no_finetune"


class ExperimentConfigRequest(BaseModel):
    preset: ExperimentMode


class ExperimentConfigResponse(BaseModel):
    preset: str
    description: str
    config: Dict[str, Any]
    current: Dict[str, Any]


# ========== 统计数据相关 ==========
class DashboardStats(BaseModel):
    """首页仪表盘数据"""
    total_experts: int
    total_knowledge: int
    total_sessions: int
    total_sft_data: int
    
    today_sessions: int
    today_avg_response_time: float
    today_accuracy: float
    
    expert_distribution: List[Dict[str, Any]]
    recent_sessions: List[Dict[str, Any]]


class ExperimentComparisonData(BaseModel):
    """实验对比数据 - 用于论文图表"""
    modes: List[str]
    avg_response_time: List[float]
    accuracy: List[float]
    cost_per_query: List[float]
    
    # 详细数据
    detailed_metrics: List[Dict[str, Any]]


class IterationProgressData(BaseModel):
    """自我迭代进度数据"""
    dates: List[str]
    knowledge_growth: List[int]
    accuracy_improvement: List[float]
    cloud_cost_reduction: List[float]


# ========== 文件上传相关 ==========
class ImageUploadResponse(BaseModel):
    filename: str
    url: str
    size: int
