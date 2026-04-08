"""会话领域模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4

from ..base.entity import AggregateRoot, ValueObject


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class QualityAssessment(ValueObject):
    """质量评估值对象"""
    overall_score: float = 0.0
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    educational_score: float = 0.0
    is_correct: bool = False
    suggestions: Optional[str] = None
    
    def is_high_quality(self, threshold: float = 4.0) -> bool:
        """是否高质量"""
        return self.overall_score >= threshold and self.is_correct


@dataclass(frozen=True)
class Message(ValueObject):
    """消息值对象"""
    id: str = field(default_factory=lambda: str(uuid4()))
    role: MessageRole = field(default=MessageRole.USER)
    content: str = ""
    image_url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # 元数据
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "image_url": self.image_url,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
        }


@dataclass  # 不使用 frozen，因为需要修改 assessment
class QAInteraction(ValueObject):
    """问答交互值对象"""
    question: Message
    answer: Message
    assessment: Optional[QualityAssessment] = None
    
    # RAG上下文
    retrieved_knowledge_ids: List[int] = field(default_factory=list)
    expert_id: Optional[int] = None
    
    def set_assessment(self, assessment: QualityAssessment) -> None:
        """设置质量评估"""
        self.assessment = assessment
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question.to_dict(),
            "answer": self.answer.to_dict(),
            "assessment": {
                "overall_score": self.assessment.overall_score if self.assessment else None,
                "is_correct": self.assessment.is_correct if self.assessment else None,
            } if self.assessment else None,
            "expert_id": self.expert_id,
            "retrieved_knowledge_ids": self.retrieved_knowledge_ids,
        }


class Session(AggregateRoot):
    """会话聚合根"""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: SessionStatus = None,
    ):
        super().__init__()
        self.session_id = session_id or str(uuid4())
        self.user_id = user_id
        self.status = status or SessionStatus.ACTIVE
        self.interactions: List[QAInteraction] = []
        self.total_questions = 0
        self.correct_count = 0
        self.avg_score = 0.0
    
    def add_interaction(self, interaction: QAInteraction) -> None:
        """添加交互"""
        self.interactions.append(interaction)
        self.total_questions += 1
        
        # 更新统计
        if interaction.assessment:
            if interaction.assessment.is_correct:
                self.correct_count += 1
            self._update_avg_score()
        
        self.update_timestamp()
    
    def _update_avg_score(self) -> None:
        """更新平均分"""
        scores = [
            i.assessment.overall_score 
            for i in self.interactions 
            if i.assessment
        ]
        if scores:
            self.avg_score = round(sum(scores) / len(scores), 2)
    
    def complete(self) -> None:
        """完成会话"""
        self.status = SessionStatus.COMPLETED
        self.update_timestamp()
    
    def mark_error(self) -> None:
        """标记错误"""
        self.status = SessionStatus.ERROR
        self.update_timestamp()
    
    def get_last_interaction(self) -> Optional[QAInteraction]:
        """获取最后一次交互"""
        return self.interactions[-1] if self.interactions else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "interactions": [i.to_dict() for i in self.interactions],
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "accuracy_rate": round(self.correct_count / self.total_questions * 100, 1) if self.total_questions > 0 else 0,
            "avg_score": self.avg_score,
        }
