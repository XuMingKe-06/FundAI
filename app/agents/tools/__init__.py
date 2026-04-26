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


# 工具名中文映射
TOOL_CHINESE_NAMES: dict = {
    "get_fund_info": "获取基金基础信息",
    "get_nav_history": "获取净值历史数据",
    "get_holdings": "获取持仓信息",
    "get_fund_manager": "获取基金经理信息",
    "get_fund_fees": "获取费率信息",
    "get_news_sentiment": "获取新闻舆情",
    "get_fund_flow": "获取资金流向",
    "get_social_heat": "获取社交媒体热度",
    "get_institutional_views": "获取机构观点",
    "get_market_index": "获取市场指数",
    "calculate_ma": "计算移动平均线",
    "calculate_macd": "计算MACD指标",
    "calculate_rsi": "计算RSI指标",
    "calculate_percentile": "计算估值分位数",
    "calculate_volatility": "计算年化波动率",
    "calculate_max_drawdown": "计算最大回撤",
    "calculate_sharpe_ratio": "计算夏普比率",
    "calculate_beta": "计算Beta系数",
}


def get_tool_chinese_name(tool_name: str) -> str:
    """
    获取工具的中文名称
    
    Args:
        tool_name: 英文工具名
        
    Returns:
        中文名称，若未匹配则返回原始英文名
    """
    return TOOL_CHINESE_NAMES.get(tool_name, tool_name)
