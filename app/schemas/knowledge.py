"""
知识库相关Schema
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class KnowledgeDocumentType(str, Enum):
    """知识库文档类型枚举"""
    ANALYSIS_REPORT = "analysis_report"  # 分析报告
    INVESTMENT_STRATEGY = "investment_strategy"  # 投资策略
    RESEARCH_REPORT = "research_report"  # 研究报告
    NEWS = "news"  # 新闻资讯


class KnowledgeDocumentBase(BaseModel):
    """知识库文档基础模型"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    doc_type: KnowledgeDocumentType = Field(..., description="文档类型")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    """知识库文档创建请求模型"""
    pass


class KnowledgeDocument(KnowledgeDocumentBase):
    """知识库文档响应模型"""
    id: str = Field(..., description="文档ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    chunk_count: int = Field(default=0, description="分块数量")

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1)
    top_k: int = Field(default=5, ge=1, le=100, description="返回数量")
    doc_type: Optional[KnowledgeDocumentType] = Field(default=None, description="文档类型过滤")
    tags: Optional[List[str]] = Field(default=None, description="标签过滤")


class KnowledgeSearchResult(BaseModel):
    """知识库搜索结果项模型"""
    content: str = Field(..., description="内容")
    score: float = Field(..., description="相似度分数")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    document_id: str = Field(..., description="文档ID")


class KnowledgeSearchResponse(BaseModel):
    """知识库搜索响应模型"""
    results: List[KnowledgeSearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="总数量")
    query: str = Field(..., description="原始查询")
