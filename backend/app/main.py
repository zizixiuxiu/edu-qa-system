"""FastAPI主应用入口"""
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.api import chat, experts, experiments, benchmark, training, knowledge, tier0, cache as cache_api
from app.services.experts.expert_pool import expert_pool
from app.services.training_executor import training_executor
from app.services.cache_service import cache_manager
from app.utils.embedding import preload_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🚀 启动教育系统...")
    init_db()
    print("✅ 数据库初始化完成")
    
    # 自动创建默认学科专家
    async with AsyncSessionLocal() as session:
        await expert_pool.ensure_default_experts(session)
    
    # 初始化缓存服务
    await cache_manager.initialize()
    
    # 预加载embedding模型（在后台线程中执行，避免阻塞）
    await asyncio.to_thread(preload_embedding_model)
    
    # 启动训练任务执行器
    await training_executor.start()
    
    yield
    # 关闭时清理
    await training_executor.stop()
    print("👋 系统关闭")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有前端地址（开发环境）
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 全局处理 OPTIONS 请求（预检请求）
from fastapi.responses import Response

@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# 全局异常处理（确保CORS头）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

# 注册路由
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(experts.router, prefix=settings.API_V1_STR)
app.include_router(knowledge.router, prefix=settings.API_V1_STR)
app.include_router(experiments.router, prefix=settings.API_V1_STR)
app.include_router(benchmark.router, prefix=settings.API_V1_STR)
app.include_router(training.router, prefix=settings.API_V1_STR)
app.include_router(tier0.router, prefix=settings.API_V1_STR)
app.include_router(cache_api.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
