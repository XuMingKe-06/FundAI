"""
应用配置模块

基于 pydantic-settings 的配置管理，支持 .env 文件和环境变量覆盖。
通过 lru_cache 实现配置单例，避免重复解析。
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # ==================== 应用基础配置 ====================
    APP_NAME: str = "FundAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ==================== 数据目录配置 ====================
    # 数据根目录，配置文件等在此目录下
    DATA_DIR: str = "./data"
    # 应用配置文件路径（JSON 格式）
    CONFIG_FILE: str = "./data/config.json"

    # 数据库配置（PostgreSQL + asyncpg 异步驱动）
    DATABASE_URL: str = "postgresql+asyncpg://fundai:fundai@localhost:5432/fundai"

    # Redis 缓存配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== 数据源配置 ====================
    TUSHARE_TOKEN: str = ""

    # ==================== CORS 配置 ====================
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ==================== RAG 配置 ====================
    # ChromaDB 向量数据库持久化目录
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    # 本地 Embedding 模型名称（EMBEDDING_MODE 为 local 时生效）
    # 注意：实际运行时由 config.json (llm.embedding_model) 优先控制，此为回退默认值
    EMBEDDING_MODEL_NAME: str = ""
    # Embedding 模式：local 使用本地模型，api 使用远程 API
    # 注意：实际运行时由 config.json (rag.embedding_mode) 优先控制，此为回退默认值
    EMBEDDING_MODE: str = "api"
    # RAG 检索返回的文档数量
    # 注意：实际运行时由 config.json (rag.top_k) 优先控制，此为回退默认值
    RAG_TOP_K: int = 5
    # 文档分块大小（字符数）
    # 注意：实际运行时由 config.json (rag.chunk_size) 优先控制，此为回退默认值
    RAG_CHUNK_SIZE: int = 500
    # 文档分块重叠大小（字符数）
    # 注意：实际运行时由 config.json (rag.chunk_overlap) 优先控制，此为回退默认值
    RAG_CHUNK_OVERLAP: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
