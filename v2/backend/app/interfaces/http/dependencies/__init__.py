"""HTTP依赖 - FastAPI依赖注入"""
from .database import get_db_session

__all__ = ["get_db_session"]
