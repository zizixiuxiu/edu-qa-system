"""系统配置 - 集中管理所有配置参数，支持实验切换"""
import os

# 设置 HuggingFace 环境变量（禁用警告，使用本地模型）
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'  # 离线模式，使用本地缓存
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """系统配置类 - 论文实验的关键控制点"""
    
    # ========== 基础配置 ==========
    PROJECT_NAME: str = "EduQASystem"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # ========== 数据库配置 ==========
    DATABASE_URL: str = "postgresql://postgres:password@localhost:15432/edu_qa"
    
    # ========== 模型配置 ==========
    LMSTUDIO_BASE_URL: str = "http://10.111.21.152:1234/v1"
    LMSTUDIO_API_KEY: str = "lm-studio"
    VL_MODEL_NAME: str = "qwen/qwen3-vl-4b"  # 专门用于图片识别的VLM模型
    LOCAL_LLM_MODEL: str = "qwen/qwen3-vl-4b"  # 使用VLM模型处理所有请求
    
    # 云端API配置
    CLOUD_API_KEY: Optional[str] = None
    CLOUD_BASE_URL: Optional[str] = None
    CLOUD_MODEL: str = "gpt-4"
    
    # ========== 专家池配置 ==========
    DEFAULT_EXPERTS: List[str] = ["数学", "物理", "化学", "语文", "英语"]
    
    # ========== 自我迭代配置 ==========
    QUALITY_THRESHOLD: float = 4.0
    DEDUP_THRESHOLD: float = 0.92
    ENABLE_CLOUD_QUALITY_CHECK: bool = True  # 启用云端质检 (Moonshot)
    ENABLE_KNOWLEDGE_UPDATE: bool = True
    
    # ========== RAG配置 ==========
    RAG_TOP_K: int = 5
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"  # HuggingFace模型名或本地路径
    EMBEDDING_DEVICE: str = "cpu"  # cpu 或 cuda
    
    # ========== 实验控制配置 ==========
    EXPERIMENT_MODE: str = "full_system"
    ENABLE_EXPERT_ROUTING: bool = True
    ENABLE_RAG: bool = True
    ENABLE_SELF_ITERATION: bool = True
    SIMULATION_MODE: bool = False
    
    # ========== 性能配置 ==========
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600
    ENABLE_ASYNC_QUEUE: bool = True
    
    # ========== Redis缓存配置 (L2层) ==========
    REDIS_ENABLED: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL_EXPERT: int = 7200  # 专家缓存2小时
    REDIS_TTL_RAG: int = 1800     # RAG结果缓存30分钟
    REDIS_TTL_VECTOR: int = 3600  # 向量缓存1小时
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 允许额外的环境变量


settings = Settings()


class ExperimentConfig:
    """实验配置管理器 - 支持一键切换实验模式"""
    
    PRESETS = {
        "baseline": {
            "EXPERIMENT_MODE": "baseline",
            "ENABLE_EXPERT_ROUTING": False,
            "ENABLE_RAG": False,
            "ENABLE_SELF_ITERATION": False,
            "ENABLE_FINETUNE": False,
            "description": "基线组：单模型 + 无RAG + 无专家路由"
        },
        "rag_only": {
            "EXPERIMENT_MODE": "rag_only",
            "ENABLE_EXPERT_ROUTING": False,
            "ENABLE_RAG": True,
            "ENABLE_SELF_ITERATION": False,
            "ENABLE_FINETUNE": False,
            "description": "RAG组：单模型 + 静态知识库"
        },
        "expert_routing": {
            "EXPERIMENT_MODE": "expert_routing",
            "ENABLE_EXPERT_ROUTING": True,
            "ENABLE_RAG": True,
            "ENABLE_SELF_ITERATION": False,
            "ENABLE_FINETUNE": False,
            "description": "专家路由组：多专家 + 动态路由 + RAG"
        },
        "full_system": {
            "EXPERIMENT_MODE": "full_system",
            "ENABLE_EXPERT_ROUTING": True,
            "ENABLE_RAG": True,
            "ENABLE_SELF_ITERATION": True,
            "description": "完整系统：专家路由+RAG+自我迭代"
        },
        "ablation_no_iteration": {
            "EXPERIMENT_MODE": "ablation_no_iteration",
            "ENABLE_EXPERT_ROUTING": True,
            "ENABLE_RAG": True,
            "ENABLE_SELF_ITERATION": False,
            "description": "消融实验：禁用自我迭代"
        }
    }
    
    @classmethod
    def apply_preset(cls, preset_name: str) -> dict:
        if preset_name not in cls.PRESETS:
            raise ValueError(f"未知预设: {preset_name}")
        
        preset = cls.PRESETS[preset_name].copy()
        del preset["description"]
        
        for key, value in preset.items():
            setattr(settings, key, value)
        
        return {
            "preset": preset_name,
            "description": cls.PRESETS[preset_name]["description"],
            "config": preset
        }
    
    @classmethod
    def get_current_config(cls) -> dict:
        return {
            "mode": settings.EXPERIMENT_MODE,
            "expert_routing": settings.ENABLE_EXPERT_ROUTING,
            "rag": settings.ENABLE_RAG,
            "self_iteration": settings.ENABLE_SELF_ITERATION,
        }
    
    @classmethod
    def list_presets(cls) -> dict:
        return {name: info["description"] for name, info in cls.PRESETS.items()}
