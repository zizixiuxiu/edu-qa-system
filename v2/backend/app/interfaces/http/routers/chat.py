"""聊天API路由 - 支持SSE流式响应和异步质检入库"""
import asyncio
import json
import time
import base64
import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from ....application.dto.chat_dto import (
    SendMessageRequest,
    SendMessageResponse,
    QualityFeedbackDTO,
)
from ....application.services.chat_service import ChatApplicationService
from ....application.services.quality_service import get_quality_checker
from ....core.config import get_settings
from ....core.logging import get_logger
from ....domain.services.routing_service import RoutingService, DefaultVLClassifier
from ....domain.services.rag_service import get_retriever
from ....infrastructure.database.repositories.expert_repository import ExpertRepository
from ....infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
from ....infrastructure.llm.client import LLMClient, get_llm_client
from ..common import success_response, error_response
from ..dependencies.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chat", tags=["聊天"])
logger = get_logger("chat_router")
settings = get_settings()

# 后台质检任务引用，防止GC
_background_tasks: set = set()


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session)
) -> ChatApplicationService:
    """获取聊天服务实例"""
    vl_classifier = DefaultVLClassifier()
    routing_service = RoutingService(vl_classifier)
    retrieval_service = get_retriever()
    expert_repo = ExpertRepository(session)
    llm_client = get_llm_client()

    return ChatApplicationService(
        routing_service=routing_service,
        retrieval_service=retrieval_service,
        expert_repo=expert_repo,
        llm_client=llm_client,
    )


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    chat_service: ChatApplicationService = Depends(get_chat_service)
):
    """发送消息 - 同步返回答案，异步执行质检入库"""
    try:
        msg = request.actual_message
        img = request.actual_image

        if not msg and not img:
            return error_response(message="消息内容不能为空")

        # 纯图片时自动补充默认提示
        if not msg and img:
            msg = "请解答图片中的题目"

        logger.info(f"Message received: {msg[:50]}")

        result = await chat_service.send_message(
            session_id=request.session_id,
            message=msg,
            image_url=img,
            force_expert=request.force_expert,
        )

        # 异步质检入库（不阻塞用户响应）
        _schedule_quality_check(
            question=msg,
            answer=result.get("answer", ""),
            expert_subject=result.get("expert_subject", "通用"),
            expert_id=result.get("expert_id"),
            session_id=result.get("session_id", ""),
        )

        # 构建响应
        response_data = {
            "success": True,
            "session_id": result.get("session_id", str(uuid4())),
            "answer": result.get("answer", ""),
            "expert_subject": result.get("expert_subject", "通用"),
            "expert_name": f"{result.get('expert_subject', '通用')}专家",
            "response_time": result.get("latency_ms", 0) / 1000,
            "expert_confidence": result.get("expert_confidence", 0.5),
            "retrieved_knowledge_count": result.get("retrieved_knowledge_count", 0),
            "used_knowledges": result.get("used_knowledges", []),
        }

        return success_response(data=response_data, message="消息处理成功")
    except Exception as e:
        logger.error(f"Send message failed: {e}", exc_info=True)
        return error_response(message=str(e))


@router.get("/stream")
async def stream_chat(
    query: str,
    session_id: Optional[str] = None,
    image: Optional[str] = None,
    force_expert: Optional[str] = None,
):
    """SSE流式问答端点 - 论文3.2节描述的流式响应"""

    async def event_generator():
        start_time = time.time()
        full_answer = ""
        expert_subject = "通用"

        try:
            # 1. 路由
            vl_classifier = DefaultVLClassifier()
            routing_service = RoutingService(vl_classifier)
            msg = query or "请解答图片中的题目"
            routing_result = await routing_service.route(
                question=msg, image_url=image, force_subject=force_expert
            )
            expert_subject = routing_result.expert_subject

            yield f"data: {json.dumps({'type': 'routing', 'expert_subject': expert_subject, 'confidence': routing_result.confidence}, ensure_ascii=False)}\n\n"

            # 2. RAG检索
            retriever = get_retriever()
            from ....infrastructure.database.connection import db
            async with db.session() as session:
                expert_repo = ExpertRepository(session)
                expert = await expert_repo.get_by_subject(expert_subject)
                expert_id = expert.id if expert else None

            rag_results = await retriever.retrieve(query=msg, expert_id=expert_id, top_k=5)
            context = "\n".join([r.content for r in rag_results]) if rag_results else ""

            knowledges = [
                {"content": r.content[:200], "tier": int(r.tier.replace("tier", "")), "score": r.similarity, "source": r.source}
                for r in rag_results
            ]
            yield f"data: {json.dumps({'type': 'retrieval', 'count': len(rag_results), 'knowledges': knowledges}, ensure_ascii=False)}\n\n"

            # 3. 流式生成
            prompt_template = routing_service.get_prompt_template(expert_subject)
            prompt = prompt_template.format(question=msg, context=context)
            messages = [{"role": "user", "content": prompt}]

            llm = get_llm_client()
            async for chunk in llm.generate_stream(messages=messages):
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'content', 'text': chunk}, ensure_ascii=False)}\n\n"

            # 4. 完成
            latency_ms = int((time.time() - start_time) * 1000)
            yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency_ms, 'expert_subject': expert_subject}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

            # 5. 异步质检
            _schedule_quality_check(
                question=msg, answer=full_answer,
                expert_subject=expert_subject, expert_id=expert_id,
                session_id=session_id or str(uuid4()),
            )

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def _schedule_quality_check(
    question: str, answer: str, expert_subject: str,
    expert_id: Optional[int], session_id: str,
):
    """调度异步质检任务（不阻塞响应）"""
    try:
        task = asyncio.create_task(
            _async_quality_check(question, answer, expert_subject, expert_id, session_id)
        )
        _background_tasks.add(task)
        task.add_done_callback(lambda t: _background_tasks.discard(t))
    except RuntimeError:
        # 没有事件循环时忽略
        pass


async def _async_quality_check(
    question: str, answer: str, expert_subject: str,
    expert_id: Optional[int], session_id: str,
):
    """异步质检并入库 - 论文3.5节自我进化闭环"""
    try:
        checker = get_quality_checker()
        result = await checker.check_quality(
            question=question, answer=answer, subject=expert_subject
        )

        logger.info(
            f"质检完成: score={result.overall_score:.1f}, "
            f"type={result.knowledge_type}, qualified={result.is_qualified}"
        )

        if not result.is_qualified:
            return

        # 去重检查
        retriever = get_retriever()
        duplicate = await retriever.check_duplicate(answer)
        if duplicate:
            logger.info(f"重复知识(相似度{duplicate[1]:.2f})，跳过入库")
            return

        # 生成向量并入库
        from ....infrastructure.embedding.bge_encoder import encode_text
        embeddings = await encode_text(answer)

        from ....infrastructure.database.connection import db
        from ....infrastructure.database.models import KnowledgeDB
        from datetime import datetime

        async with db.session() as session:
            knowledge = KnowledgeDB(
                expert_id=expert_id or 0,
                content=answer,
                embedding=embeddings[0],
                meta_data={"question": question, "answer": answer, "knowledge_type": result.knowledge_type, "source_session_id": session_id},
                tier=0,  # Tier 0
                knowledge_type=result.knowledge_type,
                quality_score=result.overall_score,
                accuracy_score=result.accuracy_score,
                completeness_score=result.completeness_score,
                educational_score=result.educational_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(knowledge)

        logger.info(f"Tier 0入库成功: score={result.overall_score:.1f}")

    except Exception as e:
        logger.error(f"异步质检失败: {e}", exc_info=True)


@router.post("/feedback")
async def submit_feedback(feedback: QualityFeedbackDTO):
    """提交质量反馈"""
    logger.info(
        f"Feedback received: session_id={feedback.session_id}, "
        f"is_correct={feedback.is_correct}, score={feedback.score}"
    )
    return success_response(message="反馈已记录")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话历史"""
    return success_response(data={"session_id": session_id, "messages": []})


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片 - 返回Base64编码"""
    try:
        contents = await file.read()

        # 限制大小 2MB
        if len(contents) > 2 * 1024 * 1024:
            return error_response(message="图片大小不能超过2MB")

        b64 = base64.b64encode(contents).decode("utf-8")
        mime = file.content_type or "image/jpeg"
        data_url = f"data:{mime};base64,{b64}"

        return success_response(
            data={"base64": data_url, "url": data_url, "filename": file.filename, "size": len(contents)},
            message="图片上传成功"
        )
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        return error_response(message="图片上传失败")
