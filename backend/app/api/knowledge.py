"""知识库管理API - CRUD操作"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional

from app.core.database import get_session
from app.models.database import Knowledge, Expert
from app.models.schemas import KnowledgeCreate, KnowledgeResponse, ResponseBase
from app.utils.embedding import embedding_service

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/list", response_model=ResponseBase)
async def list_knowledge(
    expert_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    获取知识列表
    
    Args:
        expert_id: 按专家筛选
        keyword: 关键词搜索
        page: 页码
        page_size: 每页数量
    """
    # 构建查询
    query = select(Knowledge)
    
    if expert_id:
        query = query.where(Knowledge.expert_id == expert_id)
    
    # 获取总数
    count_query = select(func.count(Knowledge.id))
    if expert_id:
        count_query = count_query.where(Knowledge.expert_id == expert_id)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(desc(Knowledge.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    knowledges = result.scalars().all()
    
    # 获取专家名称映射
    expert_ids = [k.expert_id for k in knowledges]
    expert_map = {}
    if expert_ids:
        expert_query = select(Expert).where(Expert.id.in_(expert_ids))
        expert_result = await session.execute(expert_query)
        for expert in expert_result.scalars().all():
            expert_map[expert.id] = expert.name
    
    # 构建响应
    items = []
    for k in knowledges:
        # 关键词过滤（在内存中过滤）
        if keyword and keyword.lower() not in k.content.lower():
            continue
            
        items.append({
            "id": k.id,
            "expert_id": k.expert_id,
            "expert_name": expert_map.get(k.expert_id, "未知专家"),
            "content": k.content,
            "question": k.meta_data.get("question") if k.meta_data else None,
            "source_type": k.source_type,
            "quality_score": k.quality_score,
            "usage_count": k.usage_count,
            "created_at": k.created_at.isoformat() if k.created_at else None
        })
    
    return ResponseBase(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@router.get("/{knowledge_id}", response_model=ResponseBase)
async def get_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取知识详情"""
    knowledge = await session.get(Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识点不存在", data=None)
    
    # 获取专家信息
    expert = await session.get(Expert, knowledge.expert_id)
    
    return ResponseBase(data={
        "id": knowledge.id,
        "expert_id": knowledge.expert_id,
        "expert_name": expert.name if expert else "未知专家",
        "content": knowledge.content,
        "question": knowledge.meta_data.get("question") if knowledge.meta_data else None,
        "source_type": knowledge.source_type,
        "quality_score": knowledge.quality_score,
        "usage_count": knowledge.usage_count,
        "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None
    })


@router.post("/create", response_model=ResponseBase)
async def create_knowledge(
    request: KnowledgeCreate,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    创建新知识
    
    自动计算embedding向量
    """
    # 验证专家存在
    expert = await session.get(Expert, request.expert_id)
    if not expert:
        return ResponseBase(code=404, message="专家不存在", data=None)
    
    try:
        # 计算embedding
        import numpy as np
        embedding = embedding_service.encode(request.content)
        
        # 确保embedding是列表格式
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        elif isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        # 创建知识记录
        knowledge = Knowledge(
            expert_id=request.expert_id,
            content=request.content,
            embedding=embedding,
            source_type=request.source_type,
            quality_score=4.0,  # 默认质量分数
            usage_count=0
        )
        
        session.add(knowledge)
        await session.commit()
        await session.refresh(knowledge)
        
        # 更新专家知识计数
        expert.knowledge_count += 1
        await session.commit()
        
        return ResponseBase(
            message="知识创建成功",
            data={
                "id": knowledge.id,
                "expert_id": knowledge.expert_id,
                "expert_name": expert.name,
                "content": knowledge.content,
                "source_type": knowledge.source_type,
                "quality_score": knowledge.quality_score,
                "usage_count": knowledge.usage_count,
                "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"创建失败: {str(e)}", data=None)


@router.put("/{knowledge_id}", response_model=ResponseBase)
async def update_knowledge(
    knowledge_id: int,
    request: KnowledgeCreate,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """更新知识内容"""
    knowledge = await session.get(Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识点不存在", data=None)
    
    try:
        # 如果内容变化，重新计算embedding
        if request.content != knowledge.content:
            embedding = embedding_service.encode(request.content)
            knowledge.embedding = embedding.tolist()
            knowledge.content = request.content
        
        # 更新其他字段
        knowledge.expert_id = request.expert_id
        knowledge.source_type = request.source_type
        
        await session.commit()
        await session.refresh(knowledge)
        
        # 获取专家信息
        expert = await session.get(Expert, knowledge.expert_id)
        
        return ResponseBase(
            message="知识更新成功",
            data={
                "id": knowledge.id,
                "expert_id": knowledge.expert_id,
                "expert_name": expert.name if expert else "未知专家",
                "content": knowledge.content,
                "source_type": knowledge.source_type,
                "quality_score": knowledge.quality_score,
                "usage_count": knowledge.usage_count,
                "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"更新失败: {str(e)}", data=None)


@router.delete("/{knowledge_id}", response_model=ResponseBase)
async def delete_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """删除知识"""
    knowledge = await session.get(Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识点不存在", data=None)
    
    try:
        # 更新专家知识计数
        expert = await session.get(Expert, knowledge.expert_id)
        if expert and expert.knowledge_count > 0:
            expert.knowledge_count -= 1
        
        await session.delete(knowledge)
        await session.commit()
        
        return ResponseBase(message="知识删除成功")
    except Exception as e:
        return ResponseBase(code=500, message=f"删除失败: {str(e)}", data=None)


@router.get("/stats/overview", response_model=ResponseBase)
async def get_knowledge_stats(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取知识库统计"""
    # 总数量
    total_result = await session.execute(select(func.count(Knowledge.id)))
    total = total_result.scalar()
    
    # 按专家统计
    expert_stats_query = select(
        Expert.id,
        Expert.name,
        func.count(Knowledge.id).label("count")
    ).outerjoin(
        Knowledge, Expert.id == Knowledge.expert_id
    ).group_by(Expert.id, Expert.name)
    
    expert_stats_result = await session.execute(expert_stats_query)
    expert_stats = [
        {"expert_id": row.id, "expert_name": row.name, "count": row.count}
        for row in expert_stats_result.all()
    ]
    
    # 平均质量分数
    avg_quality_result = await session.execute(
        select(func.avg(Knowledge.quality_score))
    )
    avg_quality = avg_quality_result.scalar() or 0
    
    return ResponseBase(data={
        "total_knowledge": total,
        "expert_distribution": expert_stats,
        "avg_quality_score": round(float(avg_quality), 2)
    })
