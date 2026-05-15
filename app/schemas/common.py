"""
通用响应模型
"""
from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """错误响应详情"""
    type: str = Field(..., description="错误类型")
    details: Optional[List[dict]] = Field(default=None, description="错误详情列表")


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z", description="时间戳")
    request_id: Optional[str] = Field(default=None, description="请求ID")


class PaginatedData(BaseModel, Generic[T]):
    """分页数据格式"""
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    items: List[T] = Field(..., description="数据列表")


class PaginatedResponse(ApiResponse[PaginatedData[T]], Generic[T]):
    """分页响应"""
    pass
