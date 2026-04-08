"""专家API路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ....application.dto.expert_dto import ExpertDTO, UpdateExpertRequest, ExpertStatsDTO
from ....application.services.expert_service import ExpertApplicationService
from ....core.logging import get_logger
from ..dependencies import get_db_session
from ..common import success_response, error_response

router = APIRouter(prefix="/experts", tags=["专家"])
logger = get_logger("experts_router")


def get_expert_service(session: AsyncSession = Depends(get_db_session)) -> ExpertApplicationService:
    """获取专家服务实例"""
    return ExpertApplicationService(session)


@router.get("/list")
async def list_experts(
    service: ExpertApplicationService = Depends(get_expert_service)
):
    """获取专家列表"""
    try:
        experts = await service.get_all_experts()
        return success_response(data=[ExpertDTO(**e) for e in experts])
    except Exception as e:
        logger.error(f"Failed to list experts: {e}")
        return error_response(message=str(e))


@router.get("/{expert_id}")
async def get_expert(
    expert_id: int,
    service: ExpertApplicationService = Depends(get_expert_service)
):
    """获取专家详情"""
    try:
        expert = await service.get_expert_by_id(expert_id)
        return success_response(data=ExpertDTO(**expert))
    except Exception as e:
        return error_response(message=str(e), code="NOT_FOUND")


@router.put("/{expert_id}")
async def update_expert(
    expert_id: int,
    request: UpdateExpertRequest,
    service: ExpertApplicationService = Depends(get_expert_service)
):
    """更新专家"""
    try:
        expert = await service.update_expert(
            expert_id=expert_id,
            name=request.name,
            prompt_template=request.prompt_template,
            status=request.status,
        )
        return success_response(data=ExpertDTO(**expert), message="更新成功")
    except Exception as e:
        return error_response(message=str(e))


@router.get("/subjects/list")
async def get_subjects(
    service: ExpertApplicationService = Depends(get_expert_service)
):
    """获取学科列表"""
    subjects = await service.get_subjects()
    return success_response(data={"subjects": subjects})


@router.get("/stats/summary")
async def get_stats(
    service: ExpertApplicationService = Depends(get_expert_service)
):
    """获取专家统计"""
    stats = await service.get_stats()
    return success_response(data=ExpertStatsDTO(**stats))
