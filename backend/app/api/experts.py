"""专家管理API - 按学科划分"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Optional

from app.core.database import get_session
from app.models.schemas import ExpertResponse, ExpertCreate, ResponseBase
from app.models.database import Knowledge
from app.services.experts.expert_pool import expert_pool

router = APIRouter(prefix="/experts", tags=["专家管理"])


@router.get("/list", response_model=ResponseBase)
async def list_experts(
    subject: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取专家列表"""
    experts = await expert_pool.list_experts(session, subject)
    
    data = [
        ExpertResponse(
            id=e.id,
            subject=e.subject,
            name=e.name,
            knowledge_count=e.knowledge_count,
            sft_data_count=e.sft_data_count,
            total_qa_count=e.total_qa_count,
            avg_response_time=e.avg_response_time,
            accuracy_rate=e.accuracy_rate,
            is_active=e.is_active,
            created_at=e.created_at
        )
        for e in experts
    ]
    
    return ResponseBase(data=data)


@router.get("/subjects", response_model=ResponseBase)
async def list_subjects(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取所有学科列表（包括未创建专家的）"""
    subjects = await expert_pool.list_all_subjects(session)
    # 转换为前端期望的格式 {subject, has_expert, expert_id, is_default}
    formatted = [{
        "subject": s["subject"],
        "has_expert": s.get("has_expert", False),
        "expert_id": s.get("expert_id"),
        "is_default": s.get("is_default", True)
    } for s in subjects]
    return ResponseBase(data=formatted)


@router.get("/{expert_id}", response_model=ResponseBase)
async def get_expert(
    expert_id: int,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取专家详情"""
    expert = await expert_pool.get_expert(session, expert_id)
    
    if not expert:
        return ResponseBase(code=404, message="专家不存在", data=None)
    
    return ResponseBase(data=ExpertResponse(
        id=expert.id,
        subject=expert.subject,
        name=expert.name,
        knowledge_count=expert.knowledge_count,
        sft_data_count=expert.sft_data_count,
        total_qa_count=expert.total_qa_count,
        avg_response_time=expert.avg_response_time,
        accuracy_rate=expert.accuracy_rate,
        is_active=expert.is_active,
        created_at=expert.created_at
    ))


@router.post("/create", response_model=ResponseBase)
async def create_expert(
    request: ExpertCreate,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    手动创建学科专家
    
    可用于添加新的学科专家
    """
    # 使用自定义名称或默认名称
    expert_name = request.name or f"{request.subject}专家"
    
    # 创建专家
    expert = await expert_pool.get_or_create_expert(
        session,
        request.subject
    )
    
    # 如果提供了自定义名称，更新它
    if request.name and request.name != expert.name:
        expert.name = request.name
        await session.commit()
    
    return ResponseBase(
        message="专家创建成功",
        data=ExpertResponse(
            id=expert.id,
            subject=expert.subject,
            name=expert.name,
            knowledge_count=expert.knowledge_count,
            sft_data_count=expert.sft_data_count,
            total_qa_count=expert.total_qa_count,
            avg_response_time=expert.avg_response_time,
            accuracy_rate=expert.accuracy_rate,
            is_active=expert.is_active,
            created_at=expert.created_at
        )
    )


@router.post("/{expert_id}/toggle", response_model=ResponseBase)
async def toggle_expert(
    expert_id: int,
    is_active: bool = True,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """启用/禁用专家"""
    success = await expert_pool.toggle_expert_status(session, expert_id, is_active)
    
    if success:
        status = "启用" if is_active else "禁用"
        return ResponseBase(message=f"专家已{status}")
    else:
        return ResponseBase(code=404, message="专家不存在")


@router.delete("/{expert_id}", response_model=ResponseBase)
async def delete_expert(
    expert_id: int,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """删除专家"""
    success = await expert_pool.delete_expert(session, expert_id)
    
    if success:
        return ResponseBase(message="专家已删除")
    else:
        return ResponseBase(code=404, message="专家不存在")


@router.post("/ensure-defaults", response_model=ResponseBase)
async def ensure_default_experts(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    确保默认学科专家已创建
    
    用于系统初始化，自动创建9大学科专家
    """
    subjects = await expert_pool.ensure_default_experts(session)
    
    return ResponseBase(
        message=f"成功创建 {len(subjects)} 个默认学科专家",
        data={"subjects": subjects}
    )


@router.get("/{expert_id}/knowledge-stats", response_model=ResponseBase)
async def get_expert_knowledge_stats(
    expert_id: int,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    获取专家知识库统计信息
    
    返回各类型知识的数量分布
    """
    expert = await expert_pool.get_expert(session, expert_id)
    if not expert:
        return ResponseBase(code=404, message="专家不存在", data=None)
    
    # 统计各类型的知识数量
    type_stats = {}
    for ktype in ["qa", "concept", "formula", "template", "step"]:
        count = await session.execute(
            select(func.count(Knowledge.id))
            .where(Knowledge.expert_id == expert_id)
            .where(Knowledge.knowledge_type == ktype)
        )
        type_stats[ktype] = count.scalar()
    
    # 质量分布
    high_quality = await session.execute(
        select(func.count(Knowledge.id))
        .where(Knowledge.expert_id == expert_id)
        .where(Knowledge.quality_score >= 4)
    )
    medium_quality = await session.execute(
        select(func.count(Knowledge.id))
        .where(Knowledge.expert_id == expert_id)
        .where(Knowledge.quality_score >= 3, Knowledge.quality_score < 4)
    )
    low_quality = await session.execute(
        select(func.count(Knowledge.id))
        .where(Knowledge.expert_id == expert_id)
        .where(Knowledge.quality_score < 3)
    )
    
    # 来源分布
    source_stats = {}
    for stype in ["generated", "wrong_answer_extracted", "manual"]:
        count = await session.execute(
            select(func.count(Knowledge.id))
            .where(Knowledge.expert_id == expert_id)
            .where(Knowledge.source_type == stype)
        )
        source_stats[stype] = count.scalar()
    
    return ResponseBase(data={
        "expert_id": expert_id,
        "expert_name": expert.name,
        "subject": expert.subject,
        "total_knowledge": expert.knowledge_count,
        "type_distribution": type_stats,
        "quality_distribution": {
            "high": high_quality.scalar(),
            "medium": medium_quality.scalar(),
            "low": low_quality.scalar()
        },
        "source_distribution": source_stats
    })


@router.get("/{expert_id}/knowledge", response_model=ResponseBase)
async def get_expert_knowledge_list(
    expert_id: int,
    knowledge_type: Optional[str] = Query(None, description="筛选类型: qa/concept/formula/template/step"),
    source_type: Optional[str] = Query(None, description="筛选来源: generated/wrong_answer_extracted/manual"),
    min_quality: Optional[float] = Query(None, description="最低质量分"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    获取专家知识库列表
    
    支持按类型、来源、质量分筛选，支持分页
    """
    expert = await expert_pool.get_expert(session, expert_id)
    if not expert:
        return ResponseBase(code=404, message="专家不存在", data=None)
    
    # 构建basic查询
    query = select(Knowledge).where(Knowledge.expert_id == expert_id)
    
    # 应用筛选条件
    if knowledge_type:
        query = query.where(Knowledge.knowledge_type == knowledge_type)
    if source_type:
        query = query.where(Knowledge.source_type == source_type)
    if min_quality is not None:
        query = query.where(Knowledge.quality_score >= min_quality)
    
    # 统计总数
    count_query = select(func.count(Knowledge.id)).where(Knowledge.expert_id == expert_id)
    if knowledge_type:
        count_query = count_query.where(Knowledge.knowledge_type == knowledge_type)
    if source_type:
        count_query = count_query.where(Knowledge.source_type == source_type)
    if min_quality is not None:
        count_query = count_query.where(Knowledge.quality_score >= min_quality)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # 分页查询
    query = query.order_by(Knowledge.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    knowledges = result.scalars().all()
    
    # 构建返回数据
    items = []
    for k in knowledges:
        item = {
            "id": k.id,
            "content": k.content,
            "knowledge_type": k.knowledge_type,
            "source_type": k.source_type,
            "quality_score": k.quality_score,
            "usage_count": k.usage_count,
            "meta_data": k.meta_data,
            "created_at": k.created_at.isoformat() if k.created_at else None
        }
        # 添加多维度质量评分（如果存在）
        if hasattr(k, 'accuracy_score') and k.accuracy_score is not None:
            item["accuracy_score"] = k.accuracy_score
        if hasattr(k, 'completeness_score') and k.completeness_score is not None:
            item["completeness_score"] = k.completeness_score
        if hasattr(k, 'educational_score') and k.educational_score is not None:
            item["educational_score"] = k.educational_score
        items.append(item)
    
    return ResponseBase(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    })
