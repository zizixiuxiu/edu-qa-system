"""
质检数据管理 API - 管理云端质检生成的错题知识点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_session
from app.core.config import settings
from app.models.database import Expert, Session as ChatSession, Knowledge
from app.models.schemas import ResponseBase
from app.services.iteration.data_generator import data_generator

router = APIRouter(prefix="/training", tags=["质检数据管理"])


@router.get("/pending-sessions")
async def get_pending_sessions(
    expert_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session)
):
    """
    获取待处理的质检会话列表
    （用于前端"错题知识点"页面展示）
    """
    try:
        from sqlalchemy import text
        
        sql = """
            SELECT 
                s.id,
                s.user_query as question,
                s.cloud_corrected as corrected_answer,
                s.overall_score as quality_score,
                s.accuracy_score,
                s.completeness_score,
                s.educational_score,
                s.created_at,
                e.id as expert_id,
                e.name as expert_name,
                e.subject as expert_subject,
                CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM sft_data 
                        WHERE sft_data.source_session_id = s.id
                    ) THEN 'trained'
                    ELSE 'pending'
                END as status
            FROM sessions s
            JOIN experts e ON s.expert_id = e.id
            WHERE s.cloud_corrected IS NOT NULL
              AND s.overall_score >= :threshold
        """
        params = {"threshold": settings.QUALITY_THRESHOLD}
        
        if expert_id:
            sql += " AND s.expert_id = :expert_id"
            params["expert_id"] = expert_id
        
        sql += " ORDER BY s.created_at DESC"
        
        result = await session.execute(text(sql), params)
        rows = result.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row.id,
                "expert_id": row.expert_id,
                "expert_name": row.expert_name,
                "expert_subject": row.expert_subject,
                "question": row.question[:100] + "..." if len(row.question) > 100 else row.question,
                "corrected_answer": row.corrected_answer[:200] + "..." if len(row.corrected_answer) > 200 else row.corrected_answer,
                "quality_score": row.quality_score,
                "accuracy_score": row.accuracy_score,
                "completeness_score": row.completeness_score,
                "educational_score": row.educational_score,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        # 统计
        pending_count = sum(1 for i in items if i["status"] == "pending")
        trained_count = sum(1 for i in items if i["status"] == "trained")
        
        return ResponseBase(data={
            "items": items,
            "total": len(items),
            "pending_count": pending_count,
            "trained_count": trained_count
        })
        
    except Exception as e:
        print(f"[Training] 查询待处理会话失败: {e}")
        import traceback
        traceback.print_exc()
        return ResponseBase(code=500, message=str(e), data={"items": [], "total": 0, "pending_count": 0, "trained_count": 0})


class DeletePendingRequest(BaseModel):
    """删除待处理会话请求"""
    ids: List[int]


@router.post("/pending-sessions/delete")
async def delete_pending_sessions(
    request: DeletePendingRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    批量删除待处理的质检会话
    （只删除质检结果，不删除原始会话记录）
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="未选择要删除的项")
        
        from sqlalchemy import text
        
        # 批量清除质检结果（将 cloud_corrected 等字段设为 NULL）
        placeholders = ', '.join([f':id{i}' for i in range(len(request.ids))])
        
        sql = f"""
            UPDATE sessions
            SET cloud_corrected = NULL,
                accuracy_score = NULL,
                completeness_score = NULL,
                educational_score = NULL,
                overall_score = NULL
            WHERE id IN ({placeholders})
        """
        
        params = {f'id{i}': id_val for i, id_val in enumerate(request.ids)}
        
        result = await session.execute(text(sql), params)
        await session.commit()
        
        deleted_count = result.rowcount
        
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条记录",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Training] 删除待处理会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


class AddToKnowledgeRequest(BaseModel):
    """加入知识库请求"""
    ids: List[int]


@router.post("/add-to-knowledge")
async def add_to_knowledge(
    request: AddToKnowledgeRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    将质检数据批量加入知识库
    （把云端纠正的高质量答案入库）
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="未选择要入库的项")
        
        from sqlalchemy import text
        
        # 查询选中的会话
        placeholders = ', '.join([f':id{i}' for i in range(len(request.ids))])
        params = {f'id{i}': id_val for i, id_val in enumerate(request.ids)}
        
        result = await session.execute(
            text(f"""
                SELECT 
                    s.id,
                    s.user_query,
                    s.cloud_corrected,
                    s.overall_score,
                    s.expert_id,
                    e.subject
                FROM sessions s
                JOIN experts e ON s.expert_id = e.id
                WHERE s.id IN ({placeholders})
                  AND s.cloud_corrected IS NOT NULL
            """),
            params
        )
        rows = result.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail="未找到有效的质检数据")
        
        added_count = 0
        duplicate_ids = []
        for row in rows:
            # 使用 data_generator 处理入库（自动检测知识类型）
            result = await data_generator.process_quality_answer(
                session,
                row.expert_id,
                row.user_query,
                row.cloud_corrected,
                row.overall_score,
                row.id,
                subject=row.subject,
                knowledge_type=None
            )
            if result["knowledge_added"]:
                added_count += 1
            else:
                duplicate_ids.append(row.id)
        
        duplicate_count = len(duplicate_ids)
        
        # 返回详细提示
        if added_count > 0:
            message = f"成功将 {added_count} 条记录加入知识库"
            if duplicate_count > 0:
                message += f"，{duplicate_count} 条因内容重复被跳过"
        elif duplicate_count > 0:
            message = f"{duplicate_count} 条记录因与现有知识内容重复，未入库"
        else:
            message = "未能入库，请检查数据状态"
        
        return ResponseBase(
            data={
                "success": added_count > 0,
                "message": message,
                "added_count": added_count,
                "duplicate_count": duplicate_count,
                "duplicate_ids": duplicate_ids
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Training] 加入知识库失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
