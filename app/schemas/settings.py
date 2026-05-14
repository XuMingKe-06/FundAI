"""
配置管理相关Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    """LLM配置"""
    api_base_url: str = Field(default="", description="API基础URL")
    api_key: str = Field(default="", description="API密钥")
    model: str = Field(default="", description="对话模型名称")
    embedding_api_base_url: str = Field(default="", description="Embedding API基础URL")
    embedding_api_key: str = Field(default="", description="Embedding API密钥")
    embedding_model: str = Field(default="", description="Embedding模型名称")


class DatasourceSettings(BaseModel):
    """数据源配置"""
    tushare_token: str = Field(default="", description="Tushare API Token")


class RAGSettings(BaseModel):
    """RAG配置"""
    embedding_mode: str = Field(default="api", description="Embedding模式: api 或 local")
    top_k: int = Field(default=5, description="检索Top K")
    chunk_size: int = Field(default=500, description="分块大小")
    chunk_overlap: int = Field(default=50, description="分块重叠")


class AllSettings(BaseModel):
    """所有配置"""
    llm: LLMSettings = Field(default_factory=LLMSettings, description="LLM配置")
    datasource: DatasourceSettings = Field(default_factory=DatasourceSettings, description="数据源配置")
    rag: RAGSettings = Field(default_factory=RAGSettings, description="RAG配置")


class LLMTestRequest(BaseModel):
    """LLM连接测试请求"""
    api_base_url: Optional[str] = Field(default=None, description="API基础URL")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    model: Optional[str] = Field(default=None, description="模型名称")


class LLMTestResponse(BaseModel):
    """LLM连接测试响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="测试结果消息")
    latency_ms: Optional[float] = Field(default=None, description="响应延迟(毫秒)")
