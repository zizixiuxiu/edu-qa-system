"""聊天应用服务"""
from typing import Optional
from datetime import datetime

from ...core.logging import LoggerMixin
from ...core.exceptions import ResourceNotFoundError, LLMServiceError
from ...domain.services.routing_service import RoutingService
from ...domain.services.rag_service import MultiTierRetriever
from ...infrastructure.database.repositories.expert_repository import ExpertRepository
from ...infrastructure.llm.client import LLMClient


class ChatApplicationService(LoggerMixin):
    """聊天应用服务"""
    
    def __init__(
        self,
        routing_service: RoutingService,
        retrieval_service: MultiTierRetriever,
        expert_repo: ExpertRepository,
        llm_client: LLMClient,
    ):
        self.routing = routing_service
        self.retrieval = retrieval_service
        self.expert_repo = expert_repo
        self.llm = llm_client
    
    async def send_message(
        self,
        session_id: Optional[str],
        message: str,
        image_url: Optional[str] = None,
        force_expert: Optional[str] = None,
    ) -> dict:
        """
        发送消息并获取回答
        
        流程：
        1. 获取或创建会话
        2. 专家路由
        3. RAG检索
        4. LLM生成
        5. 保存交互
        """
        import time
        start_time = time.time()
        
        # 1. 专家路由
        routing_result = await self.routing.route(
            question=message,
            image_url=image_url,
            force_subject=force_expert
        )
        
        # 2. 获取专家
        expert = await self.expert_repo.get_by_subject(routing_result.expert_subject)
        if not expert:
            raise ResourceNotFoundError(f"Expert not found: {routing_result.expert_subject}")
        
        # 3. RAG三级检索
        rag_results = await self.retrieval.retrieve(
            query=message,
            expert_id=expert.id,
            top_k=5
        )
        context = "\n".join([r.content for r in rag_results]) if rag_results else ""

        # 构建引用知识列表（返回给前端展示）
        used_knowledges = [
            {
                "content": r.content[:200],
                "tier": int(r.tier.replace("tier", "")) if isinstance(r.tier, str) else r.tier,
                "score": r.similarity,
                "source": r.source,
            }
            for r in rag_results
        ]

        # 4. 构建Prompt
        prompt_template = self.routing.get_prompt_template(expert.subject)
        prompt = prompt_template.format(
            question=message,
            context=context
        )

        # 5. LLM生成
        try:
            answer = await self.llm.generate(prompt)
        except Exception as e:
            raise LLMServiceError(f"Failed to generate answer: {e}")

        latency_ms = int((time.time() - start_time) * 1000)

        self.logger.info(
            "Message processed",
            session_id=session_id,
            expert=expert.subject,
            latency_ms=latency_ms,
            rag_count=len(rag_results)
        )

        return {
            "success": True,
            "session_id": session_id or "new_session",
            "answer": answer,
            "expert_subject": expert.subject,
            "expert_id": expert.id,
            "expert_confidence": routing_result.confidence,
            "retrieved_knowledge_count": len(rag_results),
            "used_knowledges": used_knowledges,
            "latency_ms": latency_ms,
        }
    
    async def submit_feedback(
        self,
        session_id: str,
        message_id: str,
        is_correct: bool,
        score: float,
        suggestions: Optional[str] = None
    ) -> dict:
        """提交质量反馈"""
        # 这里简化实现，实际应该保存到数据库
        self.logger.info(
            "Feedback submitted",
            session_id=session_id,
            message_id=message_id,
            is_correct=is_correct,
            score=score
        )
        
        return {
            "success": True,
            "message": "Feedback recorded"
        }
