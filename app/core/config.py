"""
应用配置模块
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "FundAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fund_analysis"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/fund_analysis"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT配置
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # LLM配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # 阿里云大模型配置
    ALIYUN_LLM_API_KEY: str = ""
    ALIYUN_LLM_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ALIYUN_EMBEDDING_MODEL: str = "text-embedding-v3"
    
    # 数据源配置
    TUSHARE_TOKEN: str = ""
    
    # 短信服务配置
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_SMS_SIGN_NAME: str = "FundAI"
    ALIYUN_SMS_TEMPLATE_CODE: str = ""
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # 限流配置
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # RAG 配置
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL_NAME: str = "text-embedding-v3"
    EMBEDDING_MODE: str = "aliyun"  # "local" 使用本地模型, "api" 使用 OpenAI API, "aliyun" 使用阿里云
    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
