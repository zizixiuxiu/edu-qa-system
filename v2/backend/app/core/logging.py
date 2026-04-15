"""日志配置 - 简化版"""
import logging
import sys
from typing import Any, Dict, Optional


def configure_logging(
    level: str = "INFO",
    format_type: str = "text",
    enable_console: bool = True
) -> None:
    """配置日志 - 简化版"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)] if enable_console else []
    )


def get_logger(name: str, **context) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


class LoggerMixin:
    """日志混入类 - 简化版"""
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
