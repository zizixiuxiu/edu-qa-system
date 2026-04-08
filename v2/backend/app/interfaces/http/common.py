"""通用响应格式"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = True
    code: str = "OK"
    message: Optional[str] = None
    data: Optional[T] = None
    
    @classmethod
    def ok(cls, data: T = None, message: str = None) -> "ApiResponse[T]":
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, message: str, code: str = "ERROR", data: T = None) -> "ApiResponse[T]":
        return cls(success=False, code=code, message=message, data=data)


def success_response(data: Any = None, message: str = None) -> dict:
    """成功响应便捷函数"""
    return {
        "success": True,
        "code": "OK",
        "message": message,
        "data": data
    }


def error_response(message: str, code: str = "ERROR", data: Any = None) -> dict:
    """错误响应便捷函数"""
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data
    }
