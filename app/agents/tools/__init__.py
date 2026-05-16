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

from app.agents.tools.advanced_technical import (
    CalculateBollingerTool,
    CalculateKDJTool,
    CalculateSupportResistanceTool
)

from app.agents.tools.advanced_risk import (
    CalculateVaRTool,
    StressTestTool,
    CalculateDownsideRiskTool
)

from app.agents.tools.advanced_analysis import (
    CalculateStyleBoxTool,
    CompareShareClassTool,
    CalculateDCATool,
    ScenarioAnalysisTool
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
    "GetMarketIndexTool",
    "CalculateBollingerTool",
    "CalculateKDJTool",
    "CalculateSupportResistanceTool",
    "CalculateVaRTool",
    "StressTestTool",
    "CalculateDownsideRiskTool",
    "CalculateStyleBoxTool",
    "CompareShareClassTool",
    "CalculateDCATool",
    "ScenarioAnalysisTool",
]


def get_available_tools() -> list:
    registry = get_tool_registry()
    return registry.list_tools()


def get_tools_info() -> list:
    registry = get_tool_registry()
    return registry.list_tools_info()


def get_tools_for_agent(agent_type: str) -> list:
    tool_mapping = {
        "fundamental": [
            "get_fund_info",
            "get_nav_history",
            "get_holdings",
            "get_fund_manager",
            "get_fund_fees",
            "calculate_style_box",
        ],
        "technical": [
            "get_nav_history",
            "calculate_ma",
            "calculate_macd",
            "calculate_rsi",
            "calculate_percentile",
            "calculate_bollinger",
            "calculate_kdj",
            "calculate_support_resistance",
        ],
        "risk": [
            "get_nav_history",
            "get_holdings",
            "calculate_volatility",
            "calculate_max_drawdown",
            "calculate_sharpe_ratio",
            "calculate_beta",
            "calculate_var",
            "stress_test",
            "calculate_downside_risk",
        ],
        "cost": [
            "get_fund_info",
            "get_fund_fees",
            "get_nav_history",
            "compare_share_class",
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
            "get_market_index",
            "calculate_dca",
            "scenario_analysis",
        ]
    }
    
    return tool_mapping.get(agent_type, [])


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
    "calculate_bollinger": "计算布林带",
    "calculate_kdj": "计算KDJ指标",
    "calculate_support_resistance": "计算支撑阻力位",
    "calculate_var": "计算VaR在险价值",
    "stress_test": "执行压力测试",
    "calculate_downside_risk": "计算下行风险",
    "calculate_style_box": "计算风格箱",
    "compare_share_class": "对比A类C类份额",
    "calculate_dca": "计算定投策略",
    "scenario_analysis": "情景分析",
}


def get_tool_chinese_name(tool_name: str) -> str:
    return TOOL_CHINESE_NAMES.get(tool_name, tool_name)
