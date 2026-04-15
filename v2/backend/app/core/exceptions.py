"""异常体系 - 企业级异常分类"""
from typing import Any, Dict, Optional
from http import HTTPStatus


class EduQAException(Exception):
    """基础异常类"""
    
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "系统内部错误"
    
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ==================== 领域异常 (Domain Exceptions) ====================

class DomainException(EduQAException):
    """领域层异常 - 业务逻辑错误"""
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "DOMAIN_ERROR"


class ExpertNotFoundError(DomainException):
    """专家不存在"""
    error_code = "EXPERT_NOT_FOUND"
    message = "指定的专家不存在"
    status_code = HTTPStatus.NOT_FOUND


class KnowledgeNotFoundError(DomainException):
    """知识不存在"""
    error_code = "KNOWLEDGE_NOT_FOUND"
    message = "指定的知识不存在"
    status_code = HTTPStatus.NOT_FOUND


class RoutingFailedError(DomainException):
    """专家路由失败"""
    error_code = "ROUTING_FAILED"
    message = "无法确定问题所属学科"


class InvalidAnswerError(DomainException):
    """答案无效"""
    error_code = "INVALID_ANSWER"
    message = "生成的答案不符合要求"


class DuplicateKnowledgeError(DomainException):
    """重复知识"""
    error_code = "DUPLICATE_KNOWLEDGE"
    message = "该知识点已存在"
    status_code = HTTPStatus.CONFLICT


# ==================== 应用异常 (Application Exceptions) ====================

class ApplicationException(EduQAException):
    """应用层异常 - 用例执行错误"""
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "APPLICATION_ERROR"


class ValidationError(ApplicationException):
    """参数验证错误"""
    error_code = "VALIDATION_ERROR"
    message = "请求参数验证失败"
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY


class UnauthorizedError(ApplicationException):
    """未授权"""
    error_code = "UNAUTHORIZED"
    message = "未授权访问"
    status_code = HTTPStatus.UNAUTHORIZED


class RateLimitError(ApplicationException):
    """限流"""
    error_code = "RATE_LIMIT"
    message = "请求过于频繁"
    status_code = HTTPStatus.TOO_MANY_REQUESTS


class ResourceNotFoundError(ApplicationException):
    """资源不存在"""
    error_code = "RESOURCE_NOT_FOUND"
    message = "请求的资源不存在"
    status_code = HTTPStatus.NOT_FOUND


# ==================== 基础设施异常 (Infrastructure Exceptions) ====================

class InfrastructureException(EduQAException):
    """基础设施层异常 - 系统错误"""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code = "INFRASTRUCTURE_ERROR"


class DatabaseError(InfrastructureException):
    """数据库错误"""
    error_code = "DATABASE_ERROR"
    message = "数据库操作失败"


class LLMServiceError(InfrastructureException):
    """LLM服务错误"""
    error_code = "LLM_SERVICE_ERROR"
    message = "LLM服务调用失败"


class EmbeddingServiceError(InfrastructureException):
    """Embedding服务错误"""
    error_code = "EMBEDDING_SERVICE_ERROR"
    message = "Embedding服务调用失败"


class CacheServiceError(InfrastructureException):
    """缓存服务错误"""
    error_code = "CACHE_SERVICE_ERROR"
    message = "缓存服务调用失败"


class StorageError(InfrastructureException):
    """存储错误"""
    error_code = "STORAGE_ERROR"
    message = "文件存储操作失败"
