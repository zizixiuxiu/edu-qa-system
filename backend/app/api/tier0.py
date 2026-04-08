"""Tier 0 知识库管理 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_session
from app.models.schemas import ResponseBase
from app.models.database import Tier0Knowledge, Expert

router = APIRouter(prefix="/tier0", tags=["Tier 0知识库"])


@router.get("/list", response_model=ResponseBase)
async def list_tier0_knowledge(
    expert_id: Optional[int] = Query(None, description="专家ID筛选"),
    subject: Optional[str] = Query(None, description="学科名称筛选"),
    knowledge_type: Optional[str] = Query(None, description="知识类型: formula/concept/template/step/qa"),
    min_score: float = Query(0.0, ge=0, le=5, description="最低质量分"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    session: AsyncSession = Depends(get_session)
):
    """获取 Tier 0 知识列表"""
    
    stmt = select(Tier0Knowledge)
    
    # 筛选条件
    if expert_id:
        stmt = stmt.where(Tier0Knowledge.expert_id == expert_id)
    elif subject:
        expert_stmt = select(Expert).where(Expert.subject == subject)
        expert_result = await session.execute(expert_stmt)
        expert = expert_result.scalar_one_or_none()
        if expert:
            stmt = stmt.where(Tier0Knowledge.expert_id == expert.id)
    
    if knowledge_type:
        stmt = stmt.where(
            Tier0Knowledge.meta_data["knowledge_type"].astext == knowledge_type
        )
    
    if min_score > 0:
        stmt = stmt.where(Tier0Knowledge.quality_score >= min_score)
    
    stmt = stmt.order_by(Tier0Knowledge.created_at.desc()).limit(limit)
    
    result = await session.execute(stmt)
    knowledges = result.scalars().all()
    
    items = []
    for k in knowledges:
        items.append({
            "id": k.id,
            "expert_id": k.expert_id,
            "content": k.content[:200] + "..." if len(k.content) > 200 else k.content,
            "quality_score": k.quality_score,
            "knowledge_type": k.meta_data.get("knowledge_type") if k.meta_data else None,
            "usage_count": k.usage_count,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "answer_preview": k.meta_data.get("answer", "")[:100] + "..." 
                             if k.meta_data and len(k.meta_data.get("answer", "")) > 100 
                             else k.meta_data.get("answer", "") if k.meta_data else ""
        })
    
    return ResponseBase(data={
        "items": items,
        "total": len(items),
        "filters": {"expert_id": expert_id, "subject": subject, 
                   "knowledge_type": knowledge_type, "min_score": min_score}
    })


@router.get("/stats", response_model=ResponseBase)
async def get_tier0_stats(session: AsyncSession = Depends(get_session)):
    """获取 Tier 0 统计信息"""
    
    # 总体统计
    total_stmt = select(func.count()).select_from(Tier0Knowledge)
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar()
    
    # 平均质量分
    avg_score_stmt = select(func.avg(Tier0Knowledge.quality_score))
    avg_score_result = await session.execute(avg_score_stmt)
    avg_score = avg_score_result.scalar() or 0
    
    # 按学科统计
    subject_stats_stmt = select(
        Expert.subject,
        func.count(Tier0Knowledge.id).label("count"),
        func.avg(Tier0Knowledge.quality_score).label("avg_score")
    ).join(Tier0Knowledge, Expert.id == Tier0Knowledge.expert_id).group_by(Expert.subject)
    
    subject_stats_result = await session.execute(subject_stats_stmt)
    subject_stats = [
        {"subject": row.subject, "count": row.count, "avg_score": round(row.avg_score or 0, 2)}
        for row in subject_stats_result.all()
    ]
    
    # 按类型统计
    type_stmt = select(
        Tier0Knowledge.meta_data["knowledge_type"].astext.label("ktype"),
        func.count().label("count")
    ).group_by("ktype")
    
    type_result = await session.execute(type_stmt)
    type_stats = [{"type": row.ktype, "count": row.count} for row in type_result.all()]
    
    return ResponseBase(data={
        "total_count": total_count,
        "avg_quality_score": round(avg_score, 2),
        "by_subject": subject_stats,
        "by_type": type_stats
    })


@router.get("/{knowledge_id}", response_model=ResponseBase)
async def get_tier0_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取单个 Tier 0 知识详情"""
    
    knowledge = await session.get(Tier0Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识不存在")
    
    expert = await session.get(Expert, knowledge.expert_id)
    
    return ResponseBase(data={
        "id": knowledge.id,
        "expert": {
            "id": expert.id if expert else None,
            "subject": expert.subject if expert else None,
            "name": expert.name if expert else None
        },
        "content": knowledge.content,
        "meta_data": knowledge.meta_data,
        "quality_score": knowledge.quality_score,
        "accuracy_score": knowledge.accuracy_score,
        "completeness_score": knowledge.completeness_score,
        "educational_score": knowledge.educational_score,
        "additional_score": knowledge.additional_score,
        "usage_count": knowledge.usage_count,
        "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None,
        "updated_at": knowledge.updated_at.isoformat() if knowledge.updated_at else None
    })


@router.delete("/{knowledge_id}", response_model=ResponseBase)
async def delete_tier0_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除 Tier 0 知识"""
    
    knowledge = await session.get(Tier0Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识不存在")
    
    expert_id = knowledge.expert_id
    await session.delete(knowledge)
    await session.commit()
    
    # 更新专家统计
    from app.services.tier0 import tier0_ingest_service
    await tier0_ingest_service._update_expert_tier0_count(session, expert_id)
    
    return ResponseBase(message="删除成功")
