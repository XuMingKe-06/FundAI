"""
工具模块初始化

导出所有工具类和注册函数
"""
from app.agents.tools.base import (
    BaseTool,
    ToolResult,
    ToolCategory,
    ToolRegistry,
    register_tool,
    get_tool_registry
)

from app.agents.tools.fund_data import (
    GetFundInfoTool,
    GetNavHistoryTool,
    GetHoldingsTool,
    GetFundManagerTool,
    GetFundFeesTool
)

from app.agents.tools.technical_indicators import (
    CalculateMATool,
    CalculateMACDTool,
    CalculateRSITool,
    CalculatePercentileTool
)

from app.agents.tools.risk_metrics import (
    CalculateVolatilityTool,
    CalculateMaxDrawdownTool,
    CalculateSharpeRatioTool,
    CalculateBetaTool
)

from app.agents.tools.market_data import (
    GetNewsSentimentTool,
    GetFundFlowTool,
    GetSocialHeatTool,
    GetInstitutionalViewsTool,
    GetMarketIndexTool
)


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolCategory",
    "ToolRegistry",
    "register_tool",
    "get_tool_registry",
    "GetFundInfoTool",
    "GetNavHistoryTool",
    "GetHoldingsTool",
    "GetFundManagerTool",
    "GetFundFeesTool",
    "CalculateMATool",
    "CalculateMACDTool",
    "CalculateRSITool",
    "CalculatePercentileTool",
    "CalculateVolatilityTool",
    "CalculateMaxDrawdownTool",
    "CalculateSharpeRatioTool",
    "CalculateBetaTool",
    "GetNewsSentimentTool",
    "GetFundFlowTool",
    "GetSocialHeatTool",
    "GetInstitutionalViewsTool",
    "GetMarketIndexTool"
]


def get_available_tools() -> list:
    """
    获取所有可用工具名称列表
    
    Returns:
        工具名称列表
    """
    registry = get_tool_registry()
    return registry.list_tools()


def get_tools_info() -> list:
    """
    获取所有工具的信息摘要
    
    Returns:
        工具信息列表
    """
    registry = get_tool_registry()
    return registry.list_tools_info()


def get_tools_for_agent(agent_type: str) -> list:
    """
    根据智能体类型获取推荐工具
    
    Args:
        agent_type: 智能体类型（fundamental/technical/risk/cost/sentiment/decision）
        
    Returns:
        推荐的工具名称列表
    """
    tool_mapping = {
        "fundamental": [
            "get_fund_info",
            "get_nav_history",
            "get_holdings",
            "get_fund_manager",
            "get_fund_fees"
        ],
        "technical": [
            "get_nav_history",
            "calculate_ma",
            "calculate_macd",
            "calculate_rsi",
            "calculate_percentile"
        ],
        "risk": [
            "get_nav_history",
            "get_holdings",
            "calculate_volatility",
            "calculate_max_drawdown",
            "calculate_sharpe_ratio",
            "calculate_beta"
        ],
        "cost": [
            "get_fund_info",
            "get_fund_fees",
            "get_nav_history"
        ],
        "sentiment": [
            "get_news_sentiment",
            "get_fund_flow",
            "get_social_heat",
            "get_institutional_views",
            "get_market_index"
        ],
        "decision": [
            "get_fund_info",
            "get_nav_history",
            "get_market_index"
        ]
    }
    
    return tool_mapping.get(agent_type, [])
