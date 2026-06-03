from typing import Dict, Any, List, Optional
import numpy as np
from loguru import logger
from app.agents.tools.base import BaseTool, ToolResult, ToolCategory, register_tool
from app.core.calculations import (
    calculate_bollinger_bands, calculate_kdj_from_nav,
    calculate_support_resistance
)

@register_tool
class CalculateBollingerTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR

    @property
    def name(self) -> str:
        return "calculate_bollinger"

    @property
    def description(self) -> str:
        return "计算布林带指标，返回上轨、中轨、下轨及信号判断"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要20个数据点"
                },
                "period": {
                    "type": "integer",
                    "description": "布林带周期，默认20",
                    "default": 20
                },
                "num_std": {
                    "type": "number",
                    "description": "标准差倍数，默认2.0",
                    "default": 2.0
                }
            },
            "required": ["values"]
        }

    async def execute(self, values: List[float], period: int = 20, num_std: float = 2.0) -> ToolResult:
        try:
            if not values or len(values) < period:
                return ToolResult.fail(
                    f"数据不足，需要至少 {period} 个数据点",
                    metadata={"data_points": len(values) if values else 0}
                )

            result = calculate_bollinger_bands(values, period, num_std)

            if not result.get("data_sufficient", False):
                return ToolResult.fail("数据不足，无法计算布林带")

            return ToolResult.ok(
                data={
                    "upper": result["upper"],
                    "middle": result["middle"],
                    "lower": result["lower"],
                    "bandwidth": result["bandwidth"],
                    "percent_b": result["percent_b"],
                    "signal": result["signal"]
                },
                metadata={"data_points": len(values), "period": period, "num_std": num_std}
            )

        except Exception as e:
            logger.error(f"计算布林带失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算布林带异常: {str(e)}")

@register_tool
class CalculateKDJTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR

    @property
    def name(self) -> str:
        return "calculate_kdj"

    @property
    def description(self) -> str:
        return "计算KDJ指标，返回K、D、J值及超买超卖信号判断"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要9个数据点"
                },
                "n": {
                    "type": "integer",
                    "description": "KDJ周期参数N，默认9",
                    "default": 9
                },
                "m1": {
                    "type": "integer",
                    "description": "KDJ平滑参数M1，默认3",
                    "default": 3
                },
                "m2": {
                    "type": "integer",
                    "description": "KDJ平滑参数M2，默认3",
                    "default": 3
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float], n: int = 9, m1: int = 3, m2: int = 3) -> ToolResult:
        try:
            if not nav_values or len(nav_values) < n:
                return ToolResult.fail(
                    f"数据不足，需要至少 {n} 个数据点",
                    metadata={"data_points": len(nav_values) if nav_values else 0}
                )

            result = calculate_kdj_from_nav(nav_values, n, m1, m2)

            if not result.get("data_sufficient", False):
                return ToolResult.fail("数据不足，无法计算KDJ")

            return ToolResult.ok(
                data={
                    "k": result["k"],
                    "d": result["d"],
                    "j": result["j"],
                    "signal": result["signal"]
                },
                metadata={"data_points": len(nav_values), "n": n, "m1": m1, "m2": m2}
            )

        except Exception as e:
            logger.error(f"计算KDJ失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算KDJ异常: {str(e)}")

@register_tool
class CalculateSupportResistanceTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR

    @property
    def name(self) -> str:
        return "calculate_support_resistance"

    @property
    def description(self) -> str:
        return "计算支撑位和阻力位，基于历史净值的关键价位识别"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要40个数据点"
                },
                "num_levels": {
                    "type": "integer",
                    "description": "识别的支撑/阻力位数量，默认3",
                    "default": 3
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float], num_levels: int = 3) -> ToolResult:
        try:
            if not nav_values or len(nav_values) < 40:
                return ToolResult.fail(
                    "数据不足，需要至少40个数据点",
                    metadata={"data_points": len(nav_values) if nav_values else 0}
                )

            result = calculate_support_resistance(nav_values, num_levels)

            if not result.get("data_sufficient", False):
                return ToolResult.fail("数据不足，无法识别支撑阻力位")

            return ToolResult.ok(
                data={
                    "support_levels": result["support_levels"],
                    "resistance_levels": result["resistance_levels"],
                    "current_nav": result["current_nav"],
                    "nearest_support": result["nearest_support"],
                    "nearest_resistance": result["nearest_resistance"],
                    "support_distance_pct": result["support_distance_pct"],
                    "resistance_distance_pct": result["resistance_distance_pct"],
                    "current_position": result["current_position"]
                },
                metadata={"data_points": len(nav_values), "num_levels": num_levels}
            )

        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算支撑阻力位异常: {str(e)}")
