"""聊天API - 核心问答接口"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
import time
import base64

from app.core.database import get_session
from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponseData, ResponseBase
from app.services.vl_service import vl_service
from app.services.experts.expert_pool import expert_pool
from app.services.experts.llm_service import llm_service
from app.services.iteration.quality_checker import quality_checker
from app.models.database import Session as ChatSession

router = APIRouter(prefix="/chat", tags=["问答"])


@router.post("/send", response_model=ResponseBase)
async def send_message(
    request: ChatRequest,
    db_session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    发送消息并获取回答 - 核心问答接口
    
    流程:
    1. VL学科识别
    2. 专家池匹配/创建
    3. RAG检索
    4. 专家推理
    5. 异步触发质检
    """
    start_time = time.time()
    
    try:
        # Step 1: VL学科识别
        vl_start = time.time()
        subject_info = await vl_service.identify_subject(
            request.query, 
            request.image
        )
        vl_time = time.time() - vl_start
        
        print(f"[Chat] 学科识别: '{request.query[:50]}...' -> {subject_info['subject']} (置信度: {subject_info.get('confidence', 'unknown')})")
        
        # Step 2: 获取或创建学科专家
        expert = await expert_pool.get_or_create_expert(
            db_session,
            subject_info["subject"]
        )
        
        # Step 3: 生成回答（使用级联RAG检索）
        use_rag = settings.ENABLE_RAG and expert.knowledge_count > 0
        
        generation_result = await llm_service.generate(
            session=db_session,
            expert=expert,
            query=request.query,
            image=request.image,
            use_rag=use_rag
        )
        
        # 记录检索统计
        rag_stats = generation_result.get("rag_stats", {})
        
        # Step 4: 创建会话记录
        session_uuid = request.session_id or str(uuid.uuid4())
        total_time = (time.time() - start_time) * 1000  # 转换为ms
        
        chat_session = ChatSession(
            session_uuid=session_uuid,
            expert_id=expert.id,
            user_query=request.query,
            user_image=request.image,
            local_answer=generation_result["answer"],
            used_knowledge_ids=[k["id"] for k in generation_result.get("used_knowledges", [])],
            response_time=total_time,
            vl_time=vl_time * 1000,
            rag_time=generation_result.get("rag_time", 0) * 1000,
            inference_time=generation_result.get("inference_time", 0) * 1000,
            experiment_mode=settings.EXPERIMENT_MODE
        )
        db_session.add(chat_session)
        await db_session.commit()
        await db_session.refresh(chat_session)
        
        # Step 5: 异步触发质检 (如果启用)
        if settings.ENABLE_SELF_ITERATION and settings.ENABLE_CLOUD_QUALITY_CHECK:
            # 实际应该用后台任务队列，这里简化处理
            import asyncio
            asyncio.create_task(
                _async_quality_check(
                    db_session, 
                    chat_session.id,
                    request.query,
                    generation_result["answer"],
                    expert.subject
                )
            )
        
        # 更新专家统计
        await expert_pool.update_expert_stats(
            db_session, 
            expert.id, 
            total_time, 
            is_accurate=True
        )
        
        return ResponseBase(
            code=200,
            message="success",
            data=ChatResponseData(
                answer=generation_result["answer"],
                session_id=session_uuid,
                expert_name=expert.name,
                expert_subject=expert.subject,
                used_knowledges=generation_result["used_knowledges"],
                response_time=total_time,
                rag_stats=rag_stats  # 返回检索统计信息
            )
        )
        
    except Exception as e:
        return ResponseBase(
            code=500,
            message=f"处理失败: {str(e)}",
            data=None
        )


async def _async_quality_check(
    session: AsyncSession,
    session_id: int,
    question: str,
    local_answer: str,
    subject: str
):
    """异步质量检查 - 只记录结果，不自动入库（带问题去重）"""
    try:
        # 调用云端质检
        quality_result = await quality_checker.check_answer(
            question, local_answer, subject
        )
        
        if not quality_result:
            return
        
        # 检查是否已存在相同问题的记录（且已有质检结果）
        from sqlalchemy import select, func
        from app.models.database import Expert
        
        # 先获取当前会话的专家信息
        current_session = await session.get(ChatSession, session_id)
        if not current_session:
            return
        
        expert = await session.get(Expert, current_session.expert_id)
        if not expert:
            return
        
        # 查找相同专家、相同问题（前50字符相似）且已有质检结果的记录
        stmt = select(ChatSession).where(
            ChatSession.expert_id == current_session.expert_id,
            func.lower(func.left(ChatSession.user_query, 50)) == func.lower(question[:50]),
            ChatSession.cloud_corrected.isnot(None),  # 已有质检结果
            ChatSession.id != session_id  # 排除当前会话
        ).order_by(ChatSession.overall_score.desc()).limit(1)
        
        result = await session.execute(stmt)
        existing_session = result.scalar_one_or_none()
        
        if existing_session:
            # 已存在相同问题的记录，比较质量分
            new_score = quality_result["overall_score"]
            existing_score = existing_session.overall_score or 0
            
            if new_score <= existing_score:
                # 新记录质量不如已有记录，标记当前会话为重复（不保存质检结果）
                print(f"[Chat] 问题重复，跳过入库 (会话{session_id}): {question[:50]}... (新:{new_score:.2f} <= 已有:{existing_score:.2f})")
                return
            else:
                # 新记录质量更高，清除旧记录的质检结果（保留更好的）
                print(f"[Chat] 发现更高质量回答，替换旧记录 (会话{session_id}): {question[:50]}... (新:{new_score:.2f} > 旧:{existing_score:.2f})")
                existing_session.cloud_corrected = None
                existing_session.overall_score = None
                existing_session.accuracy_score = None
                existing_session.completeness_score = None
                existing_session.educational_score = None
        
        # 更新当前会话的质检结果
        current_session.cloud_corrected = quality_result["corrected_answer"]
        current_session.accuracy_score = quality_result["accuracy_score"]
        current_session.completeness_score = quality_result["completeness_score"]
        current_session.educational_score = quality_result["educational_score"]
        current_session.overall_score = quality_result["overall_score"]
        # 注意：additional_score 和 knowledge_type 字段数据库中暂时不存在，需要迁移后才能使用
        
        await session.commit()
        
        # 注意：不再自动入库，改为在训练任务页面手动批量创建
        if quality_result["overall_score"] >= settings.QUALITY_THRESHOLD:
            print(f"[Chat] 质检完成 (会话{session_id}): 类型={quality_result.get('knowledge_type', 'qa')}, 质量={quality_result['overall_score']:.2f}, 待手动入库")
                    
    except Exception as e:
        print(f"[Chat] 异步质检失败: {e}")


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片 - 返回base64"""
    try:
        content = await file.read()
        base64_image = base64.b64encode(content).decode('utf-8')
        
        return ResponseBase(
            code=200,
            message="success",
            data={
                "filename": file.filename,
                "base64": base64_image,
                "size": len(content)
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=str(e), data=None)
