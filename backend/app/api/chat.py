"""聊天API - 核心问答接口"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
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
from app.services.tier0 import tier0_ingest_service  # 新增
from app.models.database import Session as ChatSession

router = APIRouter(prefix="/chat", tags=["问答"])


def get_current_experiment_config() -> Optional[Dict[str, Any]]:
    """获取当前实验配置"""
    try:
        from app.api.experiments import _current_experiment_id, _experiment_queue
        
        if not _current_experiment_id:
            return None
        
        for exp in _experiment_queue:
            if exp.id == _current_experiment_id and exp.status == "running":
                return exp.config.dict()
        return None
    except Exception:
        return None


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
        # 处理纯图片情况：如果 query 为空，使用默认提示
        user_query = request.query if request.query.strip() else "请解答图片中的题目"
        
        # 获取当前实验配置
        exp_config = get_current_experiment_config()
        
        # Step 1: VL学科识别（仅当启用专家路由时）
        vl_start = time.time()
        use_expert_routing = True  # 默认启用
        use_rag = settings.ENABLE_RAG  # 默认使用全局配置
        
        if exp_config:
            use_expert_routing = exp_config.get("use_expert_routing", True)
            use_rag = exp_config.get("use_rag", settings.ENABLE_RAG)  # 简化：use_rag 同时控制知识库
            print(f"[Chat] 实验模式: expert_routing={use_expert_routing}, rag={use_rag}")
        
        if use_expert_routing:
            subject_info = await vl_service.identify_subject(
                user_query, 
                request.image
            )
            subject = subject_info["subject"]
        else:
            # Baseline模式：强制使用通用专家
            subject_info = {"subject": "通用", "confidence": "baseline"}
            subject = "通用"
        
        vl_time = time.time() - vl_start
        
        query_display = request.query[:50] if request.query else "[图片]"
        print(f"[Chat] 学科识别: '{query_display}...' -> {subject} (路由: {'专家' if use_expert_routing else '通用'})")
        
        # Step 2: 获取或创建学科专家
        expert = await expert_pool.get_or_create_expert(
            db_session,
            subject
        )
        
        # Step 3: 生成回答（根据实验配置决定是否使用RAG）
        if exp_config:
            use_rag = use_rag and expert.knowledge_count > 0
        else:
            use_rag = settings.ENABLE_RAG and expert.knowledge_count > 0
        
        generation_result = await llm_service.generate(
            session=db_session,
            expert=expert,
            query=user_query,  # 使用处理后的查询
            image=request.image,
            use_rag=use_rag,
            use_expert_routing=use_expert_routing  # 🔥 传递专家路由开关
        )
        
        # 记录检索统计
        rag_stats = generation_result.get("rag_stats", {})
        
        # Step 4: 创建会话记录
        session_uuid = request.session_id or str(uuid.uuid4())
        total_time = (time.time() - start_time) * 1000  # 转换为ms
        
        chat_session = ChatSession(
            session_uuid=session_uuid,
            expert_id=expert.id,
            user_query=user_query,  # 使用处理后的查询
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
                    user_query,  # 使用处理后的查询
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
    """
    异步质量检查 + 自动入库到 Tier 0
    """
    try:
        # 1. 调用云端质检
        quality_result = await quality_checker.check_answer(
            question, local_answer, subject
        )
        
        if not quality_result:
            print(f"[Chat] ⚠️ 质检无结果 (会话{session_id})")
            return
        
        # 2. 获取会话和专家信息
        from app.models.database import Session as ChatSession, Expert
        
        current_session = await session.get(ChatSession, session_id)
        if not current_session:
            print(f"[Chat] ⚠️ 会话不存在 (ID: {session_id})")
            return
        
        expert = await session.get(Expert, current_session.expert_id)
        if not expert:
            print(f"[Chat] ⚠️ 专家不存在 (ID: {current_session.expert_id})")
            return
        
        # 3. 更新会话的质检结果
        current_session.cloud_corrected = quality_result["corrected_answer"]
        current_session.accuracy_score = quality_result["accuracy_score"]
        current_session.completeness_score = quality_result["completeness_score"]
        current_session.educational_score = quality_result["educational_score"]
        current_session.additional_score = quality_result.get("additional_score")
        current_session.overall_score = quality_result["overall_score"]
        current_session.knowledge_type = quality_result.get("knowledge_type", "qa")
        
        await session.commit()
        
        print(f"[Chat] ✅ 质检完成 (会话{session_id}): 类型={current_session.knowledge_type}, 质量={quality_result['overall_score']:.2f}")
        
        # 4. 自动入库到 Tier 0
        ingest_result = await tier0_ingest_service.auto_ingest(
            session=session,
            session_id=session_id,
            question=question,
            local_answer=local_answer,
            cloud_corrected=quality_result["corrected_answer"],
            quality_result=quality_result,
            expert_id=expert.id
        )
        
        if ingest_result["status"] == "success":
            print(f"[Chat] ✅ 自动入库成功 (知识ID: {ingest_result['knowledge_id']})")
        else:
            print(f"[Chat] ⚠️ 未入库: {ingest_result['reason']}")
        
    except Exception as e:
        print(f"[Chat] ❌ 异步质检/入库失败: {e}")
        import traceback
        traceback.print_exc()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片 - 返回base64（带data URL前缀）"""
    try:
        content = await file.read()
        base64_image = base64.b64encode(content).decode('utf-8')
        
        # 根据文件扩展名确定 MIME 类型
        filename = file.filename.lower()
        if filename.endswith('.png'):
            mime_type = 'image/png'
        elif filename.endswith('.gif'):
            mime_type = 'image/gif'
        elif filename.endswith('.webp'):
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'  # 默认
        
        # 添加 data URL 前缀
        data_url = f"data:{mime_type};base64,{base64_image}"
        
        return ResponseBase(
            code=200,
            message="success",
            data={
                "filename": file.filename,
                "base64": data_url,  # 返回完整的 data URL
                "raw_base64": base64_image,  # 同时返回裸 base64（供API调用使用）
                "size": len(content)
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=str(e), data=None)
