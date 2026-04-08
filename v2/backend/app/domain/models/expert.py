"""专家领域模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from ..base.entity import AggregateRoot, ValueObject


class ExpertStatus(Enum):
    """专家状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"


@dataclass  # 不使用 frozen，因为需要可变状态
class ExpertMetrics(ValueObject):
    """专家指标值对象"""
    knowledge_count: int = 0
    tier0_count: int = 0
    sft_data_count: int = 0
    total_qa_count: int = 0
    avg_response_time_ms: float = 0.0
    accuracy_rate: float = 0.0
    
    def update_accuracy(self, correct_count: int, total_count: int) -> None:
        """更新准确率（直接修改自身）"""
        if total_count > 0:
            self.accuracy_rate = round(correct_count / total_count * 100, 2)


class Expert(AggregateRoot):
    """专家聚合根"""
    
    def __init__(
        self,
        subject: str,
        name: str,
        model_type: str = "base",
        lora_path: Optional[str] = None,
        prompt_template: Optional[str] = None,
        status: ExpertStatus = None,
        metrics: ExpertMetrics = None,
    ):
        super().__init__()
        self.subject = subject
        self.name = name
        self.model_type = model_type
        self.lora_path = lora_path
        self.prompt_template = prompt_template
        self.status = status or ExpertStatus.ACTIVE
        self.metrics = metrics or ExpertMetrics()
    
    def deactivate(self) -> None:
        """停用专家"""
        self.status = ExpertStatus.INACTIVE
        self.update_timestamp()
    
    def activate(self) -> None:
        """激活专家"""
        self.status = ExpertStatus.ACTIVE
        self.update_timestamp()
    
    def update_metrics(self, metrics: ExpertMetrics) -> None:
        """更新指标"""
        self.metrics = metrics
        self.update_timestamp()
    
    def increment_qa_count(self) -> None:
        """增加问答计数"""
        self.metrics.total_qa_count += 1
        self.update_timestamp()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            **super().to_dict(),
            "subject": self.subject,
            "name": self.name,
            "model_type": self.model_type,
            "lora_path": self.lora_path,
            "prompt_template": self.prompt_template,
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True)
class RoutingResult(ValueObject):
    """路由结果值对象"""
    expert_id: int
    expert_subject: str
    confidence: float  # 置信度 0-1
    method: str  # 路由方法: vl/classifier/manual
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """是否足够置信"""
        return self.confidence >= threshold
