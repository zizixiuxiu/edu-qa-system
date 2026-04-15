"""知识领域模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from ..base.entity import AggregateRoot, ValueObject


class KnowledgeTier(Enum):
    """知识等级"""
    TIER_0 = 0  # 最高质量 - 云端质检纠正
    TIER_1 = 1  # 高质量 - 人工审核
    TIER_2 = 2  # 普通质量 - 自动入库


class KnowledgeType(Enum):
    """知识类型"""
    FORMULA = "formula"       # 公式
    CONCEPT = "concept"       # 概念
    TEMPLATE = "template"     # 解题模板
    STEP = "step"             # 步骤
    QA = "qa"                 # 问答对


@dataclass(frozen=True)
class QualityScores(ValueObject):
    """质量评分值对象"""
    overall: float = 0.0      # 总分 0-5
    accuracy: float = 0.0     # 准确性
    completeness: float = 0.0 # 完整性
    educational: float = 0.0  # 教育性
    additional: float = 0.0   # 附加分
    
    def is_qualified(self, threshold: float = 4.0) -> bool:
        """是否达到入库标准"""
        return self.overall >= threshold


@dataclass(frozen=True)
class KnowledgeMetadata(ValueObject):
    """知识元数据值对象"""
    question: str                    # 原始问题
    answer: str                      # 纠正后的答案
    local_answer: Optional[str] = None  # 本地原始答案
    knowledge_type: KnowledgeType = field(default=KnowledgeType.QA)
    source_session_id: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "local_answer": self.local_answer,
            "knowledge_type": self.knowledge_type.value,
            "source_session_id": self.source_session_id,
            "improvement_suggestions": self.improvement_suggestions,
        }


class KnowledgeItem(AggregateRoot):
    """知识项聚合根"""
    
    def __init__(
        self,
        expert_id: int,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: KnowledgeMetadata = None,
        tier: KnowledgeTier = None,
        quality: QualityScores = None,
        dedup_hash: Optional[str] = None,
    ):
        super().__init__()
        self.expert_id = expert_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or KnowledgeMetadata("", "")
        self.tier = tier or KnowledgeTier.TIER_2
        self.quality = quality or QualityScores()
        self.dedup_hash = dedup_hash
        self.usage_count = 0
    
    def upgrade_tier(self, new_tier: KnowledgeTier) -> None:
        """升级知识等级"""
        if new_tier.value < self.tier.value:
            self.tier = new_tier
            self.update_timestamp()
    
    def update_quality(self, scores: QualityScores) -> None:
        """更新质量评分"""
        self.quality = scores
        self.update_timestamp()
    
    def increment_usage(self) -> None:
        """增加使用计数"""
        self.usage_count += 1
        self.update_timestamp()
    
    def set_embedding(self, embedding: List[float]) -> None:
        """设置向量"""
        self.embedding = embedding
        self.update_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "expert_id": self.expert_id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "tier": self.tier.value,
            "tier_label": self.tier.name,
            "quality": {
                "overall": self.quality.overall,
                "accuracy": self.quality.accuracy,
                "completeness": self.quality.completeness,
                "educational": self.quality.educational,
            },
            "usage_count": self.usage_count,
        }


@dataclass(frozen=True)
class RetrievalResult(ValueObject):
    """检索结果值对象"""
    knowledge: KnowledgeItem
    similarity: float
    rank: int
    
    def is_relevant(self, threshold: float = 0.7) -> bool:
        """是否相关"""
        return self.similarity >= threshold
