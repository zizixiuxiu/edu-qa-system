"""EduQA V2 主入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.logging import configure_logging
from .core.exceptions import EduQAException
from .interfaces.http.middleware.error_handler import setup_exception_handlers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动配置
    configure_logging(
        level=settings.LOG_LEVEL,
        format_type=settings.LOG_FORMAT
    )
    
    # 初始化数据库
    from .infrastructure.database.connection import init_database, close_database
    await init_database()
    
    print(f"""
    🎓 EduQA V2 启动
    =================
    环境: {settings.APP_ENV}
    调试: {settings.DEBUG}
    版本: {settings.APP_VERSION}
    
    API文档: http://{settings.HOST}:{settings.PORT}/docs
    """)
    
    yield
    
    # 关闭清理
    await close_database()
    print("👋 EduQA V2 关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企业级教育问答系统 V2",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
setup_exception_handlers(app)


# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


# 注册API路由
from .interfaces.http.routers import chat, experts, experiments

app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(experts.router, prefix=settings.API_V1_STR)
app.include_router(experiments.router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
    )
