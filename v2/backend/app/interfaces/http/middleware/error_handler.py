"""全局异常处理中间件"""
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ....core.exceptions import EduQAException
from ....core.logging import get_logger

logger = get_logger("exception_handler")


def setup_exception_handlers(app: FastAPI) -> None:
    """设置全局异常处理器"""
    
    @app.exception_handler(EduQAException)
    async def handle_eduqa_exception(request: Request, exc: EduQAException):
        """处理自定义异常"""
        logger.warning(
            f"Business exception at {request.url.path}: "
            f"code={exc.error_code}, message={exc.message}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        """处理未捕获异常"""
        logger.error(
            f"Unhandled exception at {request.url.path}: {exc}\n{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "系统内部错误" if not logger.isEnabledFor(logging.DEBUG) else str(exc),
            },
        )
