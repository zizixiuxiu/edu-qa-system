"""数据库模型定义"""
from sqlmodel import SQLModel, Field, Relationship, Column
from pgvector.sqlalchemy import Vector
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import JSON, ARRAY, Float, Integer
import uuid


class Expert(SQLModel, table=True):
    """专家池表 - 按学科划分，支持动态扩展"""
    __tablename__ = "experts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True, unique=True)    # 学科名称: "数学" (唯一)
    name: str                                        # 显示名称: "数学专家"
    
    # 模型配置
    model_type: str = Field(default="base")          # 模型类型: base/学科名
    lora_path: Optional[str] = None                  # LoRA路径
    prompt_template: Optional[str] = None            # Prompt模板
    
    is_active: bool = Field(default=True)            # 是否启用
    
    # 统计字段
    knowledge_count: int = Field(default=0)          # Tier 1/2 知识数量
    sft_data_count: int = Field(default=0)
    total_qa_count: int = Field(default=0)
    avg_response_time: float = Field(default=0.0)
    accuracy_rate: float = Field(default=0.0)        # 准确率
    
    # 新增：Tier 0 知识数量
    tier0_count: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    knowledges: List["Knowledge"] = Relationship(back_populates="expert")
    sft_datas: List["SFTData"] = Relationship(back_populates="expert")
    sessions: List["Session"] = Relationship(back_populates="expert")
    tier0_knowledges: List["Tier0Knowledge"] = Relationship(back_populates="expert")


class Tier0Knowledge(SQLModel, table=True):
    """Tier 0 本地迭代知识库 - 高质量质检知识"""
    __tablename__ = "tier0_knowledge"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    # 检索内容（简化后的问题，用于embedding匹配）
    content: str
    embedding: List[float] = Field(sa_column=Column(Vector(384)))
    
    # 完整问答对
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))
    # meta_data格式: {
    #   "question": "原始问题",
    #   "answer": "云端纠正后的答案",
    #   "local_answer": "本地生成的答案",
    #   "knowledge_type": "formula|concept|template|step|qa",
    #   "source_session_id": 123,
    #   "improvement_suggestions": "改进建议"
    # }
    
    # 质量评分（5维度）
    quality_score: float  # 加权总分 0-5
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    additional_score: Optional[float] = None
    
    # 去重哈希（问题前100字符的MD5）
    dedup_hash: Optional[str] = Field(default=None, index=True)
    
    # 统计
    usage_count: int = Field(default=0)
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship()


class Knowledge(SQLModel, table=True):
    """知识库表 (向量存储)"""
    __tablename__ = "knowledge"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    question: str                                     # 问题
    answer: str                                       # 答案
    tier: int = Field(default=2)                      # 知识等级: 1-高质量, 2-普通
    
    embedding: List[float] = Field(sa_column=Column(Vector(384)))  # BGE-Small向量 (384维)
    content: Optional[str] = None                     # 检索内容（可为空）
    
    # 元数据
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))
    
    # 知识分类
    knowledge_type: Optional[str] = Field(default="qa", index=True)
    
    # 来源与质量
    source_type: Optional[str] = Field(default="generated")
    quality_score: float = Field(default=0.0)
    usage_count: int = Field(default=0)
    
    # 审核相关字段
    source: Optional[str] = None
    review_status: str = Field(default="approved")
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship(back_populates="knowledges")


class SFTData(SQLModel, table=True):
    """微调数据表 (Alpaca格式)"""
    __tablename__ = "sft_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    training_job_id: Optional[int] = Field(default=None, index=True)  # 关联训练任务
    
    # Alpaca格式
    instruction: str
    input: Optional[str] = None
    output: str
    
    # 来源与质量
    source_session_id: Optional[int] = None
    quality_score: float = Field(default=0.0)
    is_used_in_training: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship(back_populates="sft_datas")


class Session(SQLModel, table=True):
    """对话历史表 (实验数据统计核心)"""
    __tablename__ = "sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    # 输入输出
    user_query: str
    user_image: Optional[str] = None                 # 图片路径
    local_answer: str                                # 本地模型回答
    cloud_corrected: Optional[str] = None            # 云端纠正答案
    
    # RAG信息
    used_knowledge_ids: Optional[List[int]] = Field(sa_column=Column(ARRAY(Integer)))
    
    # 性能指标 (论文关键数据)
    response_time: float                             # 总响应时间(ms)
    vl_time: float                                   # VL识别耗时
    rag_time: float                                  # RAG检索耗时
    inference_time: float                            # 推理耗时
    
    # 质量评分
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    # 新增字段（与论文一致）
    additional_score: Optional[float] = None  # 额外维度评分
    knowledge_type: Optional[str] = None      # formula/concept/template/step/qa
    
    # 实验标记
    experiment_mode: str = Field(default="full_system")  # 记录当时实验配置
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship(back_populates="sessions")


class TrainingJob(SQLModel, table=True):
    """训练任务表"""
    __tablename__ = "training_jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")
    
    status: str = Field(default="pending")           # pending/running/completed/failed
    data_count: int
    epochs: int = Field(default=3)
    loss_history: Optional[List[float]] = Field(sa_column=Column(ARRAY(Float)))
    
    output_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExperimentMetric(SQLModel, table=True):
    """实验指标表 - 用于论文数据统计"""
    __tablename__ = "experiment_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 实验配置
    experiment_mode: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # 性能指标
    total_requests: int
    avg_response_time: float
    avg_accuracy: float
    
    # 成本指标
    cloud_api_calls: int
    local_model_calls: int
    
    # 专家分布
    expert_distribution: Dict[str, int] = Field(sa_column=Column(JSON))
    
    # 知识库增长
    total_knowledge: int
    total_sft_data: int


from sqlalchemy import Integer  # 用于ARRAY(Integer)


class BenchmarkDataset(SQLModel, table=True):
    """基准测试数据集 - 存储高考题等标准题目"""
    __tablename__ = "benchmark_datasets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str                                    # 题目内容
    correct_answer: str                              # 标准答案
    subject: str = Field(default="通用")              # 学科
    difficulty: str = Field(default="medium")        # 难度: easy/medium/hard
    source_url: Optional[str] = None                 # 数据来源URL
    
    # GAOKAO-Bench 特有字段
    year: Optional[str] = None                       # 年份
    category: Optional[str] = None                   # 卷别（全国甲卷等）
    score: Optional[int] = None                      # 分值
    analysis: Optional[str] = None                   # 解析
    question_type: str = Field(default="objective")  # objective/subjective
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BenchmarkResult(SQLModel, table=True):
    """基准测试结果 - 记录模型回答和评分"""
    __tablename__ = "benchmark_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="benchmark_datasets.id", index=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    model_answer: str                                # 模型回答
    is_correct: bool = Field(default=False)          # 是否正确
    
    # 质量评分
    accuracy_score: float = Field(default=0.0)       # 准确性
    completeness_score: float = Field(default=0.0)   # 完整性
    educational_score: float = Field(default=0.0)    # 教育性
    overall_score: float = Field(default=0.0)        # 综合得分
    
    suggestions: Optional[str] = None                # 改进建议
    
    # 迭代队列标记
    is_in_iteration_queue: bool = Field(default=False)  # 是否已加入迭代队列
    is_processed: bool = Field(default=False)           # 是否已处理生成知识点
    
    # 🔥 实验配置标识 - 区分不同实验模式的结果（Baseline/ExpertOnly/RAGOnly/FullSystem）
    experiment_config: Optional[str] = Field(default=None, index=True)
    # 🔥 实验ID - 区分同配置的多轮实验（如 FullSystem 第1/2/3轮）
    experiment_id: Optional[str] = Field(default=None, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
