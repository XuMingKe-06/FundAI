"""
Schema模块初始化
"""
from app.schemas.common import ApiResponse, PaginatedData, PaginatedResponse, ErrorResponse
from app.schemas.auth import (
    SendCodeRequest,
    SendCodeResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserInfo
)
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

__all__ = [
    # Common
    "ApiResponse",
    "PaginatedData",
    "PaginatedResponse",
    "ErrorResponse",
    # Auth
    "SendCodeRequest",
    "SendCodeResponse",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "UserInfo",
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
    "SessionDetail"
]
