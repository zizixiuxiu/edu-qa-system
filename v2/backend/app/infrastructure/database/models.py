"""数据库模型 - SQLModel定义"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlmodel import SQLModel, Field, Relationship, Column
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON


class ExpertDB(SQLModel, table=True):
    """专家表"""
    __tablename__ = "experts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True, unique=True)
    name: str
    model_type: str = Field(default="base")
    lora_path: Optional[str] = None
    prompt_template: Optional[str] = None
    status: str = Field(default="active")
    
    # 指标
    knowledge_count: int = Field(default=0)
    tier0_count: int = Field(default=0)
    sft_data_count: int = Field(default=0)
    total_qa_count: int = Field(default=0)
    avg_response_time_ms: float = Field(default=0.0)
    accuracy_rate: float = Field(default=0.0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeDB(SQLModel, table=True):
    """知识表"""
    __tablename__ = "knowledge_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    # 检索内容
    content: str
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(384)))
    
    # 元数据 (使用 meta_data 避免与 SQLAlchemy 保留字冲突)
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("meta_data", JSON))
    
    # 等级和类型
    tier: int = Field(default=2)
    knowledge_type: str = Field(default="qa")
    
    # 质量评分
    quality_score: float = Field(default=0.0)
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    
    # 去重
    dedup_hash: Optional[str] = Field(default=None, index=True)
    
    # 统计
    usage_count: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionDB(SQLModel, table=True):
    """会话表"""
    __tablename__ = "sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    user_id: Optional[str] = None
    status: str = Field(default="active")
    
    # 统计
    total_questions: int = Field(default=0)
    correct_count: int = Field(default=0)
    avg_score: float = Field(default=0.0)
    
    # 交互历史 (存储为JSON)
    interactions: List[Dict] = Field(default_factory=list, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BenchmarkResultDB(SQLModel, table=True):
    """基准测试结果表"""
    __tablename__ = "benchmark_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: str = Field(index=True)
    experiment_config: Optional[str] = Field(default=None, index=True)
    
    dataset_id: int = Field(index=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    question: str
    correct_answer: str
    model_answer: str
    
    is_correct: bool = Field(default=False)
    accuracy_score: float = Field(default=0.0)
    completeness_score: float = Field(default=0.0)
    educational_score: float = Field(default=0.0)
    overall_score: float = Field(default=0.0)
    suggestions: Optional[str] = None
    
    subject: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
