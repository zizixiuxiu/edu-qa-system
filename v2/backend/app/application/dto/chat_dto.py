"""聊天模块DTO"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """发送消息请求 - 兼容前端 query/image 和标准 message/image_url 两种字段"""
    session_id: Optional[str] = Field(default=None, description="会话ID，为空则创建新会话")
    message: Optional[str] = Field(default=None, description="用户消息")
    query: Optional[str] = Field(default=None, description="用户消息(前端兼容)")
    image_url: Optional[str] = Field(default=None, description="图片URL（可选）")
    image: Optional[str] = Field(default=None, description="图片Base64(前端兼容)")
    force_expert: Optional[str] = Field(default=None, description="强制指定专家学科")

    @property
    def actual_message(self) -> str:
        return self.message or self.query or ""

    @property
    def actual_image(self) -> Optional[str]:
        return self.image_url or self.image


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool
    session_id: str
    answer: str
    expert_subject: str
    retrieved_knowledge_count: int
    latency_ms: int


class MessageDTO(BaseModel):
    """消息DTO"""
    id: str
    role: str
    content: str
    timestamp: str


class SessionDTO(BaseModel):
    """会话DTO"""
    session_id: str
    status: str
    total_questions: int
    accuracy_rate: float
    avg_score: float
    messages: List[MessageDTO]
    created_at: str


class QualityFeedbackDTO(BaseModel):
    """质量反馈DTO"""
    session_id: str
    message_id: str
    is_correct: bool
    score: float
    suggestions: Optional[str] = None
