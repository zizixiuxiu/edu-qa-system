"""
缓存管理API - 四级缓存监控和管理

功能:
1. 查看缓存统计 (L1/L2命中率)
2. 清空指定层级缓存
3. 按模式失效缓存
4. 查看缓存健康状态
"""
from fastapi import APIRouter
from typing import Dict, Optional

from app.services.cache_service import cache_manager
from app.services.experts.expert_pool import expert_pool
from app.services.rag.retrieval_service import retrieval_service
from app.models.schemas import ResponseBase
from app.core.config import settings

router = APIRouter(prefix="/cache", tags=["缓存管理"])


@router.get("/stats", response_model=ResponseBase)
async def get_cache_stats() -> ResponseBase:
    """
    获取完整缓存统计信息
    
    包括:
    - L1内存缓存状态
    - L2 Redis缓存状态
    - 专家池缓存统计
    - RAG检索缓存统计
    - 整体命中率
    """
    try:
        # 基础缓存统计
        cache_stats = cache_manager.get_stats()
        
        # 专家池缓存统计
        expert_stats = expert_pool.get_cache_stats()
        
        # RAG检索缓存统计
        rag_stats = retrieval_service.get_cache_stats()
        
        return ResponseBase(
            code=200,
            message="success",
            data={
                "cache_service": cache_stats,
                "expert_pool": expert_stats,
                "rag_retrieval": rag_stats,
                "config": {
                    "cache_enabled": settings.ENABLE_CACHE,
                    "redis_enabled": settings.REDIS_ENABLED,
                    "redis_host": settings.REDIS_HOST if settings.REDIS_ENABLED else None,
                    "redis_port": settings.REDIS_PORT if settings.REDIS_ENABLED else None,
                    "ttl_expert": settings.REDIS_TTL_EXPERT,
                    "ttl_rag": settings.REDIS_TTL_RAG,
                    "ttl_vector": settings.REDIS_TTL_VECTOR
                }
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"获取统计失败: {str(e)}", data=None)


@router.post("/clear/{level}", response_model=ResponseBase)
async def clear_cache(level: str) -> ResponseBase:
    """
    清空指定层级的缓存
    
    Args:
        level: 缓存层级
            - "l1": 只清空L1内存缓存
            - "l2": 只清空L2 Redis缓存
            - "all": 清空所有缓存
    
    Returns:
        清空结果
    """
    try:
        if level == "l1":
            await cache_manager.l1.clear()
            return ResponseBase(
                code=200, 
                message="L1内存缓存已清空",
                data={"cleared": "L1"}
            )
        
        elif level == "l2":
            success = await cache_manager.l2.clear()
            return ResponseBase(
                code=200 if success else 500,
                message="L2 Redis缓存已清空" if success else "L2清空失败",
                data={"cleared": "L2", "success": success}
            )
        
        elif level == "all":
            await cache_manager.clear_all()
            return ResponseBase(
                code=200,
                message="所有缓存已清空",
                data={"cleared": "all"}
            )
        
        else:
            return ResponseBase(
                code=400,
                message=f"无效的缓存层级: {level}。可选: l1, l2, all",
                data=None
            )
    
    except Exception as e:
        return ResponseBase(code=500, message=f"清空缓存失败: {str(e)}", data=None)


@router.post("/invalidate", response_model=ResponseBase)
async def invalidate_cache(pattern: str) -> ResponseBase:
    """
    按模式失效缓存
    
    Args:
        pattern: 缓存key匹配模式
            - "expert": 失效所有专家缓存
            - "rag": 失效所有RAG检索缓存
            - "vector": 失效所有向量缓存
            - 其他: 自定义匹配模式
    
    Returns:
        失效结果
    """
    try:
        # 映射常见模式
        pattern_map = {
            "expert": "expert",
            "rag": "rag_retrieval",
            "vector": "vector"
        }
        
        actual_pattern = pattern_map.get(pattern, pattern)
        
        await cache_manager.invalidate_pattern(actual_pattern)
        
        return ResponseBase(
            code=200,
            message=f"缓存模式 '{pattern}' 已失效",
            data={"pattern": pattern, "actual": actual_pattern}
        )
    
    except Exception as e:
        return ResponseBase(code=500, message=f"失效缓存失败: {str(e)}", data=None)


@router.get("/health", response_model=ResponseBase)
async def cache_health() -> ResponseBase:
    """
    缓存健康检查
    
    检查:
    - L1内存缓存状态
    - L2 Redis连接状态
    - 缓存命中率是否正常
    """
    try:
        health = {
            "status": "healthy",
            "checks": {}
        }
        
        # L1检查
        l1_stats = cache_manager.l1.get_stats()
        health["checks"]["l1_memory"] = {
            "status": "ok",
            "size": l1_stats["size"],
            "hit_rate": l1_stats["hit_rate"]
        }
        
        # L2检查
        l2_stats = cache_manager.l2.get_stats()
        health["checks"]["l2_redis"] = {
            "status": "connected" if l2_stats["connected"] else "disconnected",
            "host": l2_stats.get("host"),
            "hit_rate": l2_stats["hit_rate"]
        }
        
        if not l2_stats["connected"]:
            health["status"] = "degraded"
            health["checks"]["l2_redis"]["recommendation"] = "Redis未连接，系统仅使用L1内存缓存"
        
        # 整体评估
        overall = cache_manager._calculate_overall_stats()
        if overall.get("overall_hit_rate"):
            hit_rate_value = overall.get("overall_hit_rate_value", 0)
            if hit_rate_value < 0.3 and overall.get("total_requests", 0) > 100:
                health["status"] = "warning"
                health["checks"]["hit_rate"] = {
                    "status": "low",
                    "value": overall["overall_hit_rate"],
                    "recommendation": "缓存命中率偏低，建议检查缓存配置"
                }
        
        return ResponseBase(
            code=200,
            message="健康检查完成",
            data=health
        )
    
    except Exception as e:
        return ResponseBase(code=500, message=f"健康检查失败: {str(e)}", data=None)


@router.post("/toggle", response_model=ResponseBase)
async def toggle_cache(enabled: bool) -> ResponseBase:
    """
    全局启用/禁用缓存
    
    Args:
        enabled: 是否启用缓存
    
    Returns:
        操作结果
    """
    try:
        old_value = settings.ENABLE_CACHE
        settings.ENABLE_CACHE = enabled
        
        return ResponseBase(
            code=200,
            message=f"缓存已{'启用' if enabled else '禁用'}",
            data={
                "previous": old_value,
                "current": enabled,
                "note": "此设置仅影响当前进程，重启后恢复配置文件设置"
            }
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"切换缓存状态失败: {str(e)}", data=None)


@router.get("/config", response_model=ResponseBase)
async def get_cache_config() -> ResponseBase:
    """获取当前缓存配置"""
    return ResponseBase(
        code=200,
        message="success",
        data={
            "enable_cache": settings.ENABLE_CACHE,
            "redis": {
                "enabled": settings.REDIS_ENABLED,
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                "has_password": settings.REDIS_PASSWORD is not None
            },
            "ttl": {
                "default": settings.CACHE_TTL,
                "expert": settings.REDIS_TTL_EXPERT,
                "rag": settings.REDIS_TTL_RAG,
                "vector": settings.REDIS_TTL_VECTOR
            },
            "l1_memory": {
                "max_size": 1000,
                "eviction_policy": "LRU"
            }
        }
    )
