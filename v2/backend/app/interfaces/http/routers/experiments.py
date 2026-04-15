"""实验API路由"""
import asyncio

from fastapi import APIRouter
from typing import List, Set

from ....application.dto.experiment_dto import (
    ExperimentConfigDTO,
    ExperimentQueueItemDTO,
    BenchmarkProgressDTO,
)
from ....application.services.experiment_service import ExperimentApplicationService
from ....core.logging import LoggerMixin
from ..common import success_response, error_response

router = APIRouter(prefix="/experiments", tags=["实验"])
logger = LoggerMixin()

# 全局实验服务实例
experiment_service = ExperimentApplicationService()

# 保存后台任务引用，防止垃圾回收
background_tasks: Set[asyncio.Task] = set()

def _cleanup_task(task: asyncio.Task) -> None:
    """任务完成后清理引用"""
    background_tasks.discard(task)


@router.post("/create")
async def create_experiments(request: dict):
    """创建实验"""
    try:
        configs = [ExperimentConfigDTO(**e) for e in request.get("experiments", [])]
        experiment_ids = await experiment_service.create_experiments(configs)
        return success_response(
            data={"experiment_ids": experiment_ids},
            message=f"成功创建 {len(experiment_ids)} 个实验"
        )
    except Exception as e:
        logger.error(f"Create experiments failed: {e}")
        return error_response(message=str(e))


@router.get("/queue")
async def get_queue():
    """获取实验队列"""
    queue_data = await experiment_service.get_queue()
    return success_response(data=queue_data)


@router.post("/start")
async def start_experiments():
    """启动实验队列"""
    next_exp = await experiment_service.start_next()
    if next_exp:
        # 在后台执行实验，保存任务引用防止GC
        task = asyncio.create_task(experiment_service.execute_current_experiment())
        background_tasks.add(task)
        task.add_done_callback(_cleanup_task)
        return success_response(
            data=next_exp.to_dict(),
            message="实验已启动并在后台执行"
        )
    else:
        return error_response(message="没有待运行的实验或已有实验在运行")


@router.post("/clear")
async def clear_queue():
    """清空实验队列"""
    await experiment_service.clear_queue()
    return success_response(message="队列已清空")


@router.get("/progress")
async def get_progress():
    """获取当前实验进度"""
    return success_response(data=BenchmarkProgressDTO(
        status="idle",
        current=0,
        total=0,
        current_question="",
        elapsed_time=0
    ))


@router.post("/run-all")
async def run_all_experiments():
    """一键运行全部6组实验"""
    default_experiments = [
        ExperimentConfigDTO(
            name="① Baseline基线（无路由无RAG）",
            use_rag=False,
            use_expert_routing=False,
            enable_iteration=False,
        ),
        ExperimentConfigDTO(
            name="② ExpertOnly（有路由无RAG）",
            use_rag=False,
            use_expert_routing=True,
            enable_iteration=False,
        ),
        ExperimentConfigDTO(
            name="③ FullSystem第1轮（建库）",
            use_rag=True,
            use_expert_routing=True,
            enable_iteration=True,
        ),
        ExperimentConfigDTO(
            name="④ RAGOnly（有库后）",
            use_rag=True,
            use_expert_routing=False,
            enable_iteration=False,
        ),
        ExperimentConfigDTO(
            name="⑤ FullSystem第2轮（进化1）",
            use_rag=True,
            use_expert_routing=True,
            enable_iteration=True,
        ),
        ExperimentConfigDTO(
            name="⑥ FullSystem第3轮（进化2）",
            use_rag=True,
            use_expert_routing=True,
            enable_iteration=True,
        ),
    ]
    
    experiment_ids = await experiment_service.create_experiments(default_experiments)
    next_exp = await experiment_service.start_next()
    
    return success_response(
        data={
            "experiment_count": len(experiment_ids),
            "started": next_exp is not None
        },
        message="已创建6组实验并开始运行"
    )
