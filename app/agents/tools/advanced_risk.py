from typing import Dict, Any, List, Optional
import numpy as np
import logging

from app.agents.tools.base import BaseTool, ToolResult, ToolCategory, register_tool
from app.core.calculations import (
    calculate_var, calculate_cvar, calculate_downside_risk, stress_test
)

logger = logging.getLogger(__name__)


@register_tool
class CalculateVaRTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC

    @property
    def name(self) -> str:
        return "calculate_var"

    @property
    def description(self) -> str:
        return "计算VaR（在险价值），返回95%和99%置信度下的日度VaR"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要20个数据点"
                },
                "confidence_level": {
                    "type": "number",
                    "description": "置信度水平，默认0.95",
                    "default": 0.95
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float], confidence_level: float = 0.95) -> ToolResult:
        try:
            values = np.array([v for v in nav_values if v > 0])
            if len(values) < 20:
                return ToolResult.fail("数据不足，需要至少20个数据点")

            returns = np.diff(values) / values[:-1]

            var_95 = calculate_var(returns, 0.95)
            var_99 = calculate_var(returns, 0.99)
            cvar_95 = calculate_cvar(returns, 0.95)
            downside = calculate_downside_risk(returns)

            return ToolResult.ok(
                data={
                    "var_95_pct": round(var_95 * 100, 4) if var_95 is not None else None,
                    "var_99_pct": round(var_99 * 100, 4) if var_99 is not None else None,
                    "cvar_95_pct": round(cvar_95 * 100, 4) if cvar_95 is not None else None,
                    "downside_risk_pct": downside,
                    "confidence_level": confidence_level,
                    "data_points": len(values)
                },
                metadata={"data_points": len(values)}
            )

        except Exception as e:
            logger.error(f"计算VaR失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算VaR异常: {str(e)}")


@register_tool
class StressTestTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC

    @property
    def name(self) -> str:
        return "stress_test"

    @property
    def description(self) -> str:
        return "执行压力测试，模拟极端市场情景下的基金损失，包含2015股灾、2020疫情等场景"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要30个数据点"
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float]) -> ToolResult:
        try:
            values = np.array([v for v in nav_values if v > 0])
            if len(values) < 30:
                return ToolResult.fail("数据不足，需要至少30个数据点")

            result = stress_test(values)

            if not result.get("data_sufficient", False):
                return ToolResult.fail(result.get("error", "压力测试失败"))

            return ToolResult.ok(
                data={
                    "scenarios": result["scenarios"],
                    "var_95": result["var_95"],
                    "var_99": result["var_99"],
                    "cvar_95": result["cvar_95"],
                    "downside_risk": result["downside_risk"],
                    "current_nav": result["current_nav"]
                },
                metadata={"data_points": len(values)}
            )

        except Exception as e:
            logger.error(f"压力测试失败: {e}", exc_info=True)
            return ToolResult.fail(f"压力测试异常: {str(e)}")


@register_tool
class CalculateDownsideRiskTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC

    @property
    def name(self) -> str:
        return "calculate_downside_risk"

    @property
    def description(self) -> str:
        return "计算下行风险（Downside Risk），仅考虑低于阈值的收益率波动"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列"
                },
                "threshold": {
                    "type": "number",
                    "description": "阈值收益率，默认0.0",
                    "default": 0.0
                }
            },
            "required": ["nav_values"]
        }

    async def execute(self, nav_values: List[float], threshold: float = 0.0) -> ToolResult:
        try:
            values = np.array([v for v in nav_values if v > 0])
            if len(values) < 10:
                return ToolResult.fail("数据不足，需要至少10个数据点")

            returns = np.diff(values) / values[:-1]
            downside = calculate_downside_risk(returns, threshold)

            return ToolResult.ok(
                data={
                    "downside_risk_pct": downside,
                    "threshold": threshold,
                    "data_points": len(values)
                },
                metadata={"data_points": len(values)}
            )

        except Exception as e:
            logger.error(f"计算下行风险失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算下行风险异常: {str(e)}")
