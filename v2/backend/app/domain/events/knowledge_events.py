"""知识领域事件"""
from dataclasses import dataclass
from typing import Optional

from ...core.events import DomainEvent


@dataclass(frozen=True)
class KnowledgeCreated(DomainEvent):
    """知识创建事件"""
    knowledge_id: int
    expert_id: int
    content_preview: str  # 内容预览(前100字符)


@dataclass(frozen=True)
class KnowledgeUpdated(DomainEvent):
    """知识更新事件"""
    knowledge_id: int
    expert_id: int
    changes: list  # 变更字段列表


@dataclass(frozen=True)
class KnowledgeUsed(DomainEvent):
    """知识被使用事件"""
    knowledge_id: int
    session_id: str
    similarity: float


@dataclass(frozen=True)
class QualityCheckCompleted(DomainEvent):
    """质量检查完成事件"""
    session_id: str
    interaction_index: int
    overall_score: float
    is_correct: bool
    should_add_to_knowledge: bool


@dataclass(frozen=True)
class KnowledgeTierUpgraded(DomainEvent):
    """知识等级提升事件"""
    knowledge_id: int
    old_tier: int
    new_tier: int
    reason: str
