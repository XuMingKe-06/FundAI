from typing import Dict, Any, List, Optional
import logging

from app.agents.tools.base import BaseTool, ToolResult, ToolCategory, register_tool
from app.core.calculations import (
    calculate_style_box, estimate_share_class_fees,
    calculate_dca_analysis, calculate_scenario_analysis
)

logger = logging.getLogger(__name__)


@register_tool
class CalculateStyleBoxTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA

    @property
    def name(self) -> str:
        return "calculate_style_box"

    @property
    def description(self) -> str:
        return "计算基金九宫格风格箱（大盘/中盘/小盘 x 价值/平衡/成长），基于持仓数据判断"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "holdings": {
                    "type": "object",
                    "description": "持仓数据，包含 stock_list 字段"
                }
            },
            "required": ["holdings"]
        }

    async def execute(self, holdings: Dict[str, Any]) -> ToolResult:
        try:
            if not holdings:
                return ToolResult.fail("持仓数据为空")

            result = calculate_style_box(holdings)

            if not result.get("data_sufficient", False):
                return ToolResult.fail("持仓数据不足，无法判断风格")

            return ToolResult.ok(
                data={
                    "market_cap_style": result["market_cap_style"],
                    "value_style": result["value_style"],
                    "style_box_position": result["style_box_position"],
                    "top_stocks_style": result.get("top_stocks_style", [])
                },
                metadata={"data_sufficient": True}
            )

        except Exception as e:
            logger.error(f"计算风格箱失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算风格箱异常: {str(e)}")


@register_tool
class CompareShareClassTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA

    @property
    def name(self) -> str:
        return "compare_share_class"

    @property
    def description(self) -> str:
        return "对比A类和C类份额的总成本，基于持有期计算最优份额类别"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fees_data": {
                    "type": "object",
                    "description": "费率数据，包含 purchase_fee、redemption_fee、management_fee、sales_service_fee 等字段"
                }
            },
            "required": ["fees_data"]
        }

    async def execute(self, fees_data: Dict[str, Any]) -> ToolResult:
        try:
            if not fees_data:
                return ToolResult.fail("费率数据为空")

            result = estimate_share_class_fees(fees_data)

            if not result.get("data_sufficient", False):
                return ToolResult.fail("费率数据不足，无法对比份额类别")

            return ToolResult.ok(
                data={
                    "comparison": result["comparison"],
                    "crossover_day": result["crossover_day"],
                    "recommendation": result["recommendation"]
                },
                metadata={"data_sufficient": True}
            )

        except Exception as e:
            logger.error(f"对比份额类别失败: {e}", exc_info=True)
            return ToolResult.fail(f"对比份额类别异常: {str(e)}")


@register_tool
class CalculateDCATool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA

    @property
    def name(self) -> str:
        return "calculate_dca"

    @property
    def description(self) -> str:
        return "计算定投策略分析，对比定投与一次性投入的收益差异，检测微笑曲线"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要10个数据点"
                },
                "investment_amount": {
                    "type": "number",
                    "description": "每次定投金额，默认1000",
                    "default": 1000
                },
                "frequency_days": {
                    "type": "integer",
                    "description": "定投频率（天），默认7天",
                    "default": 7
                }
            },
            "required": ["nav_values"]
        }

    async def execute(
        self,
        nav_values: List[float],
        investment_amount: float = 1000,
        frequency_days: int = 7
    ) -> ToolResult:
        try:
            if not nav_values or len(nav_values) < 10:
                return ToolResult.fail("数据不足，需要至少10个数据点")

            result = calculate_dca_analysis(nav_values, investment_amount, frequency_days)

            if not result.get("data_sufficient", False):
                return ToolResult.fail(result.get("error", "定投分析失败"))

            return ToolResult.ok(
                data={
                    "dca": result["dca"],
                    "lump_sum": result["lump_sum"],
                    "comparison": result["comparison"],
                    "smile_curve": result["smile_curve"]
                },
                metadata={"data_points": len(nav_values)}
            )

        except Exception as e:
            logger.error(f"定投分析失败: {e}", exc_info=True)
            return ToolResult.fail(f"定投分析异常: {str(e)}")


@register_tool
class ScenarioAnalysisTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA

    @property
    def name(self) -> str:
        return "scenario_analysis"

    @property
    def description(self) -> str:
        return "执行情景分析，分析牛市/熊市/震荡市不同情景下的历史表现和当前市场状态"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要60个数据点"
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float]) -> ToolResult:
        try:
            if not nav_values or len(nav_values) < 60:
                return ToolResult.fail("数据不足，需要至少60个数据点")

            result = calculate_scenario_analysis(nav_values)

            if not result.get("data_sufficient", False):
                return ToolResult.fail(result.get("error", "情景分析失败"))

            return ToolResult.ok(
                data={
                    "bull_market": result["bull_market"],
                    "bear_market": result["bear_market"],
                    "sideways_market": result["sideways_market"],
                    "current_regime": result["current_regime"]
                },
                metadata={"data_points": len(nav_values)}
            )

        except Exception as e:
            logger.error(f"情景分析失败: {e}", exc_info=True)
            return ToolResult.fail(f"情景分析异常: {str(e)}")
