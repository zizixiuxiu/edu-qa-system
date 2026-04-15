"""
实验管理 API - 控制变量实验系统
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import os

from app.core.database import get_session
from app.core.config import settings

router = APIRouter(prefix="/experiments", tags=["实验管理"])


# ============= 数据模型 =============

class ExperimentConfig(BaseModel):
    """实验配置（简化版）"""
    name: str
    description: Optional[str] = ""
    random_seed: int = 42  # 随机种子
    
    # 实验变量（简化：只用 use_rag 和 use_expert_routing 两个开关）
    use_rag: bool = False              # RAG知识检索（true=启用知识库+RAG）
    use_expert_routing: bool = True    # 专家路由（true=使用学科专家prompt，false=无角色prompt）
    enable_iteration: bool = True      # 自动入库（仅FullSystem应启用）
    
    prompt_template: str = "default"
    max_questions: Optional[int] = None
    
    # 筛选条件
    subject: Optional[str] = None
    year: Optional[str] = None


class ExperimentCreateRequest(BaseModel):
    """创建实验请求"""
    experiments: List[ExperimentConfig]


class ExperimentStatus(BaseModel):
    """实验状态"""
    id: str
    name: str
    status: str  # pending/running/completed/failed
    config: ExperimentConfig
    progress: int = 0
    current_question: int = 0
    total_questions: int = 0
    result_path: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============= 全局状态 =============

_experiment_queue: List[ExperimentStatus] = []
_current_experiment_id: Optional[str] = None
EXPERIMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "experiments")
os.makedirs(EXPERIMENTS_DIR, exist_ok=True)

# 重置函数（用于清理）
def reset_experiment_queue():
    global _experiment_queue, _current_experiment_id
    _experiment_queue = []
    _current_experiment_id = None
    print("[Experiment] 实验队列已重置")


# ============= API 路由 =============

@router.post("/create")
async def create_experiments(request: ExperimentCreateRequest):
    """创建实验队列"""
    global _experiment_queue
    
    created_experiments = []
    for idx, config in enumerate(request.experiments):
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}"
        
        experiment = ExperimentStatus(
            id=exp_id,
            name=config.name,
            status="pending",
            config=config,
            created_at=datetime.now().isoformat()
        )
        
        _experiment_queue.append(experiment)
        created_experiments.append(experiment)
    
    return {
        "success": True,
        "message": f"成功创建 {len(created_experiments)} 组实验",
        "experiments": [e.dict() for e in created_experiments]
    }


@router.get("/queue")
async def get_experiment_queue():
    """获取当前实验队列"""
    return {
        "current_id": _current_experiment_id,
        "queue": [e.dict() for e in _experiment_queue],
        "total": len(_experiment_queue),
        "pending": len([e for e in _experiment_queue if e.status == "pending"]),
        "running": len([e for e in _experiment_queue if e.status == "running"]),
        "completed": len([e for e in _experiment_queue if e.status == "completed"])
    }


@router.post("/start")
async def start_experiments():
    """开始执行实验队列"""
    global _current_experiment_id
    
    pending_exp = None
    for exp in _experiment_queue:
        if exp.status == "pending":
            pending_exp = exp
            break
    
    if not pending_exp:
        return {"success": False, "message": "没有待执行的实验"}
    
    _current_experiment_id = pending_exp.id
    pending_exp.status = "running"
    pending_exp.started_at = datetime.now().isoformat()
    
    return {
        "success": True,
        "message": "实验开始",
        "experiment": pending_exp.dict()
    }


@router.get("/current")
async def get_current_experiment():
    """获取当前正在执行的实验"""
    if not _current_experiment_id:
        return {"success": False, "message": "没有正在执行的实验"}
    
    for exp in _experiment_queue:
        if exp.id == _current_experiment_id:
            return {"success": True, "experiment": exp.dict()}
    
    return {"success": False, "message": "未找到当前实验"}


@router.post("/{experiment_id}/update")
async def update_experiment_progress(
    experiment_id: str,
    progress: int,
    current_question: int = 0,
    total_questions: int = 0
):
    """更新实验进度"""
    for exp in _experiment_queue:
        if exp.id == experiment_id:
            exp.progress = progress
            exp.current_question = current_question
            exp.total_questions = total_questions
            return {"success": True}
    
    return {"success": False, "message": "实验不存在"}


@router.post("/{experiment_id}/complete")
async def complete_experiment(experiment_id: str, result_data: Dict[str, Any]):
    """完成实验并保存数据"""
    global _current_experiment_id
    
    for exp in _experiment_queue:
        if exp.id == experiment_id:
            exp.status = "completed"
            exp.completed_at = datetime.now().isoformat()
            exp.progress = 100
            
            # 保存实验数据
            exp_dir = os.path.join(EXPERIMENTS_DIR, experiment_id)
            os.makedirs(exp_dir, exist_ok=True)
            
            experiment_data = {
                "experiment_info": {
                    "id": exp.id,
                    "name": exp.name,
                    "description": exp.config.description,
                    "created_at": exp.created_at,
                    "started_at": exp.started_at,
                    "completed_at": exp.completed_at,
                },
                "config": exp.config.dict(),
                "results": result_data
            }
            
            result_path = os.path.join(exp_dir, "experiment_data.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(experiment_data, f, ensure_ascii=False, indent=2)
            
            exp.result_path = result_path
            
            # 检查是否还有下一个实验
            next_exp = None
            for e in _experiment_queue:
                if e.status == "pending":
                    next_exp = e
                    break
            
            if next_exp:
                _current_experiment_id = next_exp.id
                next_exp.status = "running"
                next_exp.started_at = datetime.now().isoformat()
                return {
                    "success": True,
                    "message": "当前实验完成，开始下一个",
                    "next_experiment": next_exp.dict()
                }
            else:
                _current_experiment_id = None
                return {
                    "success": True,
                    "message": "所有实验完成",
                    "all_completed": True
                }
    
    return {"success": False, "message": "实验不存在"}


@router.get("/list")
async def list_experiments():
    """列出所有实验"""
    experiments = []
    for exp in _experiment_queue:
        experiments.append({
            "id": exp.id,
            "name": exp.name,
            "status": exp.status,
            "progress": exp.progress,
            "created_at": exp.created_at,
            "result_path": exp.result_path
        })
    
    return {"experiments": experiments}


@router.delete("/clear")
async def clear_experiments():
    """清空实验队列"""
    global _experiment_queue, _current_experiment_id
    _experiment_queue = []
    _current_experiment_id = None
    return {"success": True, "message": "实验队列已清空"}


@router.get("/current-config")
async def get_current_config():
    """获取当前实验配置（兼容旧接口）"""
    if _current_experiment_id:
        for exp in _experiment_queue:
            if exp.id == _current_experiment_id:
                return {
                    "code": 200,
                    "data": {
                        "mode": "experiment",
                        "experiment_id": exp.id,
                        "config": exp.config.dict()
                    }
                }
    
    return {
        "code": 200,
        "data": {
            "mode": "default",
            "experiment_id": None,
            "config": {}
        }
    }


@router.get("/presets")
async def get_presets():
    """获取实验预设列表"""
    return {
        "code": 200,
        "data": {
            "baseline": "基线组（无RAG无专家路由）",
            "rag_only": "仅RAG组（无专家路由）",
            "expert_only": "仅专家路由组（无RAG）⭐",
            "knowledge_only": "仅知识库组",
            "full_system": "完整系统（RAG+专家路由）",
            "ablation_rag": "消融实验-RAG效果",
            "ablation_knowledge": "消融实验-知识库效果"
        }
    }


@router.post("/config")
async def set_config(request: dict):
    """设置实验配置（兼容旧接口）"""
    preset = request.get("preset", "full_system")
    
    # 预设配置映射（简化版：只用 use_rag 和 use_expert_routing）
    preset_configs = {
        "baseline": {"use_rag": False, "use_expert_routing": False},
        "rag_only": {"use_rag": True, "use_expert_routing": False},
        "expert_only": {"use_rag": False, "use_expert_routing": True},
        "full_system": {"use_rag": True, "use_expert_routing": True},
    }
    
    config = preset_configs.get(preset, preset_configs["full_system"])
    
    return {
        "code": 200,
        "message": f"已应用预设: {preset}",
        "data": {
            "preset": preset,
            "current": config
        }
    }


@router.get("/subjects")
async def get_subjects():
    """获取学科列表"""
    return {
        "code": 200,
        "data": [
            {"value": "数学", "label": "数学"},
            {"value": "语文", "label": "语文"},
            {"value": "英语", "label": "英语"},
            {"value": "物理", "label": "物理"},
            {"value": "化学", "label": "化学"},
            {"value": "生物", "label": "生物"},
            {"value": "历史", "label": "历史"},
            {"value": "地理", "label": "地理"},
            {"value": "政治", "label": "政治"}
        ]
    }


@router.get("/dashboard")
async def get_dashboard(session: AsyncSession = Depends(get_session)):
    """获取实验仪表盘数据（首页概览）"""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from app.models.database import Expert, Knowledge, Tier0Knowledge, Session, SFTData
    
    # 统计专家数量
    experts_result = await session.execute(select(func.count(Expert.id)))
    total_experts = experts_result.scalar() or 0
    
    # 统计知识条目 (Knowledge + Tier0Knowledge)
    knowledge_result = await session.execute(select(func.count(Knowledge.id)))
    total_knowledge = knowledge_result.scalar() or 0
    tier0_result = await session.execute(select(func.count(Tier0Knowledge.id)))
    total_tier0 = tier0_result.scalar() or 0
    total_knowledge_entries = total_knowledge + total_tier0
    
    # 统计问答总数
    sessions_result = await session.execute(select(func.count(Session.id)))
    total_sessions = sessions_result.scalar() or 0
    
    # 统计微调数据
    sft_result = await session.execute(select(func.count(SFTData.id)))
    total_sft_data = sft_result.scalar() or 0
    
    # 今日数据
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions_result = await session.execute(
        select(func.count(Session.id)).where(Session.created_at >= today_start)
    )
    today_sessions = today_sessions_result.scalar() or 0
    
    # 今日平均响应时间
    today_avg_time_result = await session.execute(
        select(func.avg(Session.response_time)).where(Session.created_at >= today_start)
    )
    today_avg_response_time = today_avg_time_result.scalar() or 0
    
    # 今日准确率 (有评分的数据)
    today_accuracy_result = await session.execute(
        select(func.avg(Session.overall_score))
        .where(Session.created_at >= today_start)
        .where(Session.overall_score.isnot(None))
    )
    today_accuracy = today_accuracy_result.scalar()
    today_accuracy = round(today_accuracy * 20, 1) if today_accuracy else 0  # 转换为百分比 (5分制->100分制)
    
    return {
        "code": 200,
        "data": {
            "total_experts": total_experts,
            "total_knowledge": total_knowledge_entries,
            "total_sessions": total_sessions,
            "total_sft_data": total_sft_data,
            "today_sessions": today_sessions,
            "today_avg_response_time": round(today_avg_response_time, 0),
            "today_accuracy": today_accuracy
        }
    }


@router.get("/comparison")
async def get_comparison():
    """获取实验对比数据"""
    return {
        "code": 200,
        "data": []
    }


@router.get("/iteration-progress")
async def get_iteration_progress(days: int = 30):
    """获取迭代进度"""
    return {
        "code": 200,
        "data": {
            "days": days,
            "progress": []
        }
    }


@router.get("/export-data")
async def export_data(format: str = "json"):
    """导出实验数据"""
    data = {
        "experiments": [e.dict() for e in _experiment_queue],
        "export_time": datetime.now().isoformat()
    }
    
    if format == "json":
        return {
            "code": 200,
            "data": data
        }
    else:
        return {
            "code": 200,
            "data": {
                "content": str(data),
                "format": format
            }
        }
