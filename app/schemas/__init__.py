"""
Schema模块初始化
"""
from app.schemas.common import ApiResponse, PaginatedData, PaginatedResponse, ErrorResponse
from app.schemas.fund import (
    FundSearchRequest,
    FundListItem,
    FundDetail,
    NavData,
    NavHistoryResponse,
    HoldingItem,
    HoldingsResponse,
    FeeItem,
    FeesResponse
)
from app.schemas.analysis import (
    CreateSessionRequest,
    SessionInfo,
    CreateSessionResponse,
    AgentStatusEvent,
    ThinkingEvent,
    ToolCallEvent,
    AgentCompleteEvent,
    AnalysisCompleteEvent,
    ShortTermDecision,
    LongTermDecision,
    CostMatrixItem,
    TrendChart,
    AgentScores,
    AnalysisReport,
    SessionListItem,
    AgentOutputInfo,
    SessionDetail
)
from app.schemas.settings import (
    LLMSettings,
    DatasourceSettings,
    RAGSettings,
    AllSettings,
    LLMTestRequest,
    LLMTestResponse
)

__all__ = [
    # Common
    "ApiResponse",
    "PaginatedData",
    "PaginatedResponse",
    "ErrorResponse",
    # Fund
    "FundSearchRequest",
    "FundListItem",
    "FundDetail",
    "NavData",
    "NavHistoryResponse",
    "HoldingItem",
    "HoldingsResponse",
    "FeeItem",
    "FeesResponse",
    # Analysis
    "CreateSessionRequest",
    "SessionInfo",
    "CreateSessionResponse",
    "AgentStatusEvent",
    "ThinkingEvent",
    "ToolCallEvent",
    "AgentCompleteEvent",
    "AnalysisCompleteEvent",
    "ShortTermDecision",
    "LongTermDecision",
    "CostMatrixItem",
    "TrendChart",
    "AgentScores",
    "AnalysisReport",
    "SessionListItem",
    "AgentOutputInfo",
    "SessionDetail",
    # Settings
    "LLMSettings",
    "DatasourceSettings",
    "RAGSettings",
    "AllSettings",
    "LLMTestRequest",
    "LLMTestResponse",
]
