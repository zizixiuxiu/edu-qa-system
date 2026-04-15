"""配置管理 - 环境分离的企业级配置"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # 应用基础配置
    APP_NAME: str = Field(default="EduQA", description="应用名称")
    APP_VERSION: str = Field(default="2.0.0", description="应用版本")
    APP_ENV: str = Field(default="development", description="环境: development/testing/production")
    DEBUG: bool = Field(default=True, description="调试模式")
    
    # API配置
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 安全配置
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # CORS配置
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # 数据库配置
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:password@localhost:15432/edu_qa",
        description="数据库连接URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="连接池大小")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="连接池溢出")
    DATABASE_ECHO: bool = Field(default=False, description="SQL日志")
    
    # Redis配置
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    REDIS_POOL_SIZE: int = Field(default=50, description="Redis连接池")
    
    # LLM配置 (主模型 - 本地 LM Studio)
    LLM_BASE_URL: str = Field(default="http://10.111.21.152:1234/v1", description="LLM API基础URL")
    LLM_API_KEY: Optional[str] = Field(default="not-needed", description="LLM API密钥")
    LLM_MODEL: str = Field(default="qwen/qwen3-vl-4b", description="主LLM模型")
    LLM_TIMEOUT: float = Field(default=120.0, description="LLM超时(秒)")
    LLM_MAX_RETRIES: int = Field(default=3, description="LLM重试次数")
    
    # Kimi/Moonshot 配置 (云端质检/高质量模型)
    KIMI_BASE_URL: str = Field(default="https://api.moonshot.cn/v1", description="Kimi API基础URL")
    KIMI_API_KEY: Optional[str] = Field(default="sk-exeOu7RTp3Z01hjyOjkMJ22XeiFU3PaTWUrm6Q7AiabeK8b6", description="Kimi API密钥")
    KIMI_MODEL: str = Field(default="kimi-k2-5", description="Kimi模型")
    
    # VL模型配置 (使用本地LM Studio部署的Qwen3-VL-4B)
    VL_MODEL: str = Field(default="qwen/qwen3-vl-4b", description="视觉语言模型")
    VL_TIMEOUT: float = Field(default=30.0, description="VL超时(秒)")
    VL_BASE_URL: str = Field(default="http://10.111.21.152:1234/v1", description="VL服务URL")
    
    # Embedding配置
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-small-zh-v1.5", description="Embedding模型")
    EMBEDDING_DIMENSION: int = Field(default=384, description="向量维度")
    EMBEDDING_DEVICE: str = Field(default="cpu", description="运行设备")
    
    # RAG配置
    RAG_TOP_K: int = Field(default=5, description="RAG检索Top-K")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="相似度阈值")
    
    # 知识库配置
    KNOWLEDGE_QUALITY_THRESHOLD: float = Field(default=4.0, description="入库质量阈值")
    KNOWLEDGE_DEDUP_THRESHOLD: float = Field(default=0.92, description="去重相似度阈值")
    
    # 实验配置
    BENCHMARK_DEFAULT_QUESTIONS: int = Field(default=50, description="默认题目数")
    BENCHMARK_DELAY_SECONDS: float = Field(default=5.0, description="题目间延迟")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(default="json", description="日志格式: json/text")
    
    # 文件存储
    DATA_DIR: str = Field(default="./data", description="数据目录")
    REPORTS_DIR: str = Field(default="./data/reports", description="报告目录")
    UPLOADS_DIR: str = Field(default="./data/uploads", description="上传目录")
    
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"
    
    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
