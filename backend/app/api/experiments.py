"""实验控制API - 论文核心"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_session
from app.core.config import settings, ExperimentConfig
from app.models.schemas import (
    ExperimentConfigRequest, 
    ExperimentConfigResponse,
    ExperimentComparisonData,
    IterationProgressData,
    DashboardStats,
    ResponseBase
)
from app.models.database import Session as ChatSession, Expert, Knowledge, SFTData, ExperimentMetric

router = APIRouter(prefix="/experiments", tags=["实验控制"])


@router.get("/presets", response_model=ResponseBase)
async def list_presets() -> ResponseBase:
    """列出所有实验预设"""
    return ResponseBase(data=ExperimentConfig.list_presets())


@router.post("/config", response_model=ResponseBase)
async def set_experiment_config(
    request: ExperimentConfigRequest
) -> ResponseBase:
    """设置实验配置 - 一键切换实验模式"""
    result = ExperimentConfig.apply_preset(request.preset.value)
    current = ExperimentConfig.get_current_config()
    
    return ResponseBase(data=ExperimentConfigResponse(
        preset=result["preset"],
        description=result["description"],
        config=result["config"],
        current=current
    ))


@router.get("/current-config", response_model=ResponseBase)
async def get_current_config() -> ResponseBase:
    """获取当前实验配置"""
    return ResponseBase(data=ExperimentConfig.get_current_config())


@router.get("/dashboard", response_model=ResponseBase)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """获取仪表盘统计数据"""
    
    # 基础统计
    total_experts = await session.execute(select(func.count(Expert.id)))
    total_knowledge = await session.execute(select(func.count(Knowledge.id)))
    total_sessions = await session.execute(select(func.count(ChatSession.id)))
    total_sft = await session.execute(select(func.count(SFTData.id)))
    
    # 今日统计
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    today_sessions_result = await session.execute(
        select(func.count(ChatSession.id)).where(ChatSession.created_at >= today_start)
    )
    today_sessions = today_sessions_result.scalar()
    
    today_avg_time = await session.execute(
        select(func.avg(ChatSession.response_time)).where(
            ChatSession.created_at >= today_start
        )
    )
    
    today_accuracy = await session.execute(
        select(func.avg(ChatSession.overall_score)).where(
            ChatSession.created_at >= today_start,
            ChatSession.overall_score.isnot(None)
        )
    )
    
    # 专家分布
    experts = await session.execute(select(Expert))
    expert_list = experts.scalars().all()
    expert_distribution = [
        {"name": e.name, "count": e.total_qa_count}
        for e in sorted(expert_list, key=lambda x: x.total_qa_count, reverse=True)[:10]
    ]
    
    # 最近会话
    recent = await session.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).limit(5)
    )
    recent_sessions = [
        {
            "id": s.id,
            "query": s.user_query[:50] + "..." if len(s.user_query) > 50 else s.user_query,
            "expert_id": s.expert_id,
            "response_time": s.response_time,
            "created_at": s.created_at.isoformat()
        }
        for s in recent.scalars().all()
    ]
    
    return ResponseBase(data=DashboardStats(
        total_experts=total_experts.scalar(),
        total_knowledge=total_knowledge.scalar(),
        total_sessions=total_sessions.scalar(),
        total_sft_data=total_sft.scalar(),
        today_sessions=today_sessions,
        today_avg_response_time=round(today_avg_time.scalar() or 0, 2),
        today_accuracy=round((today_accuracy.scalar() or 0) / 5 * 100, 2),  # 转换为百分比
        expert_distribution=expert_distribution,
        recent_sessions=recent_sessions
    ))


@router.get("/comparison", response_model=ResponseBase)
async def get_experiment_comparison(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    获取实验对比数据 - 用于论文图表
    对比不同实验模式的性能
    """
    modes = ["baseline", "rag_only", "expert_routing", "full_system"]
    
    # 查询各模式的历史数据
    metrics = []
    for mode in modes:
        result = await session.execute(
            select(
                func.avg(ChatSession.response_time),
                func.avg(ChatSession.overall_score),
                func.count(ChatSession.id)
            ).where(ChatSession.experiment_mode == mode)
        )
        avg_time, avg_score, count = result.one()
        
        # 估算成本 (云端调用次数 * 单价)
        cloud_calls = await session.execute(
            select(func.count(ChatSession.id)).where(
                ChatSession.experiment_mode == mode,
                ChatSession.cloud_corrected.isnot(None)
            )
        )
        
        metrics.append({
            "mode": mode,
            "avg_response_time": round(avg_time or 0, 2),
            "accuracy": round((avg_score or 3) / 5 * 100, 2),  # 转换为百分比
            "total_queries": count or 0,
            "cloud_cost": (cloud_calls.scalar() or 0) * 0.02  # 假设每次$0.02
        })
    
    return ResponseBase(data=ExperimentComparisonData(
        modes=modes,
        avg_response_time=[m["avg_response_time"] for m in metrics],
        accuracy=[m["accuracy"] for m in metrics],
        cost_per_query=[m["cloud_cost"] / max(m["total_queries"], 1) for m in metrics],
        detailed_metrics=metrics
    ))


@router.get("/iteration-progress", response_model=ResponseBase)
async def get_iteration_progress(
    days: int = 30,
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """
    获取自我迭代进度 - 用于论文图表
    展示知识库增长和准确率提升
    """
    dates = []
    knowledge_growth = []
    accuracy_improvement = []
    cloud_cost_reduction = []
    
    for i in range(days, 0, -1):
        date = datetime.utcnow() - timedelta(days=i)
        dates.append(date.strftime("%m-%d"))
        
        # 累计知识库数量
        knowledge_count = await session.execute(
            select(func.count(Knowledge.id)).where(
                Knowledge.created_at <= date
            )
        )
        knowledge_growth.append(knowledge_count.scalar())
        
        # 当日准确率
        day_start = date.replace(hour=0, minute=0, second=0)
        day_end = date.replace(hour=23, minute=59, second=59)
        
        accuracy = await session.execute(
            select(func.avg(ChatSession.overall_score)).where(
                ChatSession.created_at >= day_start,
                ChatSession.created_at <= day_end
            )
        )
        acc_value = accuracy.scalar()
        accuracy_improvement.append(round((acc_value or 0) / 5 * 100, 2))
        
        # 云端调用占比 (越低越好)
        total = await session.execute(
            select(func.count(ChatSession.id)).where(
                ChatSession.created_at >= day_start,
                ChatSession.created_at <= day_end
            )
        )
        cloud = await session.execute(
            select(func.count(ChatSession.id)).where(
                ChatSession.created_at >= day_start,
                ChatSession.created_at <= day_end,
                ChatSession.cloud_corrected.isnot(None)
            )
        )
        total_count = total.scalar() or 1
        cloud_count = cloud.scalar() or 0
        cloud_cost_reduction.append(round(cloud_count / total_count * 100, 2))
    
    return ResponseBase(data=IterationProgressData(
        dates=dates,
        knowledge_growth=knowledge_growth,
        accuracy_improvement=accuracy_improvement,
        cloud_cost_reduction=cloud_cost_reduction
    ))


@router.post("/record-metric")
async def record_experiment_metric(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """记录当前实验指标 - 用于定期统计"""
    
    # 统计当前指标
    total_requests = await session.execute(select(func.count(ChatSession.id)))
    avg_time = await session.execute(select(func.avg(ChatSession.response_time)))
    avg_accuracy = await session.execute(
        select(func.avg(ChatSession.overall_score)).where(
            ChatSession.overall_score.isnot(None)
        )
    )
    
    cloud_calls = await session.execute(
        select(func.count(ChatSession.id)).where(
            ChatSession.cloud_corrected.isnot(None)
        )
    )
    
    local_calls = await session.execute(
        select(func.count(ChatSession.id)).where(
            ChatSession.cloud_corrected.is_(None)
        )
    )
    
    # 专家分布
    experts = await session.execute(select(Expert))
    expert_dist = {e.name: e.total_qa_count for e in experts.scalars().all()}
    
    # 知识库统计
    total_knowledge = await session.execute(select(func.count(Knowledge.id)))
    total_sft = await session.execute(select(func.count(SFTData.id)))
    
    metric = ExperimentMetric(
        experiment_mode=settings.EXPERIMENT_MODE,
        total_requests=total_requests.scalar(),
        avg_response_time=avg_time.scalar() or 0,
        avg_accuracy=avg_accuracy.scalar() or 0,
        cloud_api_calls=cloud_calls.scalar(),
        local_model_calls=local_calls.scalar(),
        expert_distribution=expert_dist,
        total_knowledge=total_knowledge.scalar(),
        total_sft_data=total_sft.scalar()
    )
    
    session.add(metric)
    await session.commit()
    
    return ResponseBase(message="指标记录成功")


@router.get("/export-data")
async def export_experiment_data(
    format: str = "json",
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    """导出实验数据 - 用于论文分析"""
    
    # 导出所有会话数据
    result = await session.execute(select(ChatSession))
    sessions = result.scalars().all()
    
    data = [
        {
            "id": s.id,
            "experiment_mode": s.experiment_mode,
            "expert_id": s.expert_id,
            "response_time": s.response_time,
            "vl_time": s.vl_time,
            "rag_time": s.rag_time,
            "inference_time": s.inference_time,
            "overall_score": s.overall_score,
            "created_at": s.created_at.isoformat()
        }
        for s in sessions
    ]
    
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)
        
        return ResponseBase(data={
            "format": "csv",
            "content": output.getvalue()
        })
    
    return ResponseBase(data={
        "format": "json",
        "count": len(data),
        "data": data
    })
