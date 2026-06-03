"""
风险指标计算工具

提供波动率、最大回撤、夏普比率、Beta系数等风险指标计算工具
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from loguru import logger
from app.agents.tools.base import (
    BaseTool, 
    ToolResult, 
    ToolCategory, 
    register_tool
)
from app.core.calculations import (
    calculate_volatility, calculate_max_drawdown,
    calculate_sharpe_ratio, calculate_beta
)

@register_tool
class CalculateVolatilityTool(BaseTool):
    """
    计算年化波动率工具
    
    基于净值序列计算年化波动率
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC
    
    @property
    def name(self) -> str:
        return "calculate_volatility"
    
    @property
    def description(self) -> str:
        return "计算年化波动率，基于净值序列计算，返回百分比形式的年化波动率"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值序列数组，按时间升序排列"
                },
                "annualization_factor": {
                    "type": "integer",
                    "description": "年化因子，默认252（交易日）",
                    "default": 252
                }
            },
            "required": ["nav_values"]
        }
    
    async def execute(
        self, 
        nav_values: List[float], 
        annualization_factor: int = 252
    ) -> ToolResult:
        """
        执行波动率计算
        
        Args:
            nav_values: 净值序列
            annualization_factor: 年化因子
            
        Returns:
            计算结果
        """
        try:
            values = np.array([v for v in nav_values if v > 0])
            
            if len(values) < 2:
                return ToolResult.fail("净值数据不足，至少需要2个数据点")
            
            returns = np.diff(values) / values[:-1]
            
            if len(returns) < 2:
                return ToolResult.fail("收益率数据不足")
            
            annual_volatility = calculate_volatility(returns, annualization_factor)
            daily_volatility = round(float(np.std(returns, ddof=1) * 100), 4)
            
            return ToolResult.ok(
                data={
                    "annual_volatility": annual_volatility,
                    "daily_volatility": daily_volatility,
                    "data_points": len(values),
                    "return_points": len(returns)
                }
            )
            
        except Exception as e:
            logger.error(f"计算波动率失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算波动率异常: {str(e)}")

@register_tool
class CalculateMaxDrawdownTool(BaseTool):
    """
    计算最大回撤工具
    
    计算净值序列的最大回撤及发生位置
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC
    
    @property
    def name(self) -> str:
        return "calculate_max_drawdown"
    
    @property
    def description(self) -> str:
        return "计算最大回撤，返回最大回撤百分比、回撤开始位置和结束位置"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值序列数组，按时间升序排列"
                }
            },
            "required": ["nav_values"]
        }
    
    async def execute(self, nav_values: List[float]) -> ToolResult:
        """
        执行最大回撤计算
        
        Args:
            nav_values: 净值序列
            
        Returns:
            计算结果
        """
        try:
            values = np.array([v for v in nav_values if v > 0])
            
            if len(values) < 2:
                return ToolResult.fail("净值数据不足，至少需要2个数据点")
            
            max_drawdown, max_dd_end_idx = calculate_max_drawdown(values)
            if max_dd_end_idx is None:
                max_dd_end_idx = 0
            
            max_dd_start_idx = 0
            peak_value = values[0]
            for i in range(max_dd_end_idx + 1):
                if values[i] > peak_value:
                    peak_value = values[i]
                    max_dd_start_idx = i
            
            return ToolResult.ok(
                data={
                    "max_drawdown": round(float(max_drawdown), 2),
                    "start_index": int(max_dd_start_idx),
                    "end_index": int(max_dd_end_idx),
                    "peak_value": round(float(values[max_dd_start_idx]), 4),
                    "trough_value": round(float(values[max_dd_end_idx]), 4),
                    "data_points": len(values)
                }
            )
            
        except Exception as e:
            logger.error(f"计算最大回撤失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算最大回撤异常: {str(e)}")

@register_tool
class CalculateSharpeRatioTool(BaseTool):
    """
    计算夏普比率工具
    
    基于净值序列计算夏普比率
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC
    
    @property
    def name(self) -> str:
        return "calculate_sharpe_ratio"
    
    @property
    def description(self) -> str:
        return "计算夏普比率，基于净值序列和无风险利率计算风险调整后收益"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值序列数组，按时间升序排列"
                },
                "risk_free_rate": {
                    "type": "number",
                    "description": "无风险年化利率，默认0.02（2%）",
                    "default": 0.02
                },
                "annualization_factor": {
                    "type": "integer",
                    "description": "年化因子，默认252（交易日）",
                    "default": 252
                }
            },
            "required": ["nav_values"]
        }
    
    async def execute(
        self, 
        nav_values: List[float], 
        risk_free_rate: float = 0.02,
        annualization_factor: int = 252
    ) -> ToolResult:
        """
        执行夏普比率计算
        
        Args:
            nav_values: 净值序列
            risk_free_rate: 无风险利率
            annualization_factor: 年化因子
            
        Returns:
            计算结果
        """
        try:
            values = np.array([v for v in nav_values if v > 0])
            
            if len(values) < 2:
                return ToolResult.fail("净值数据不足，至少需要2个数据点")
            
            returns = np.diff(values) / values[:-1]
            
            if len(returns) < 2:
                return ToolResult.fail("收益率数据不足")
            
            sharpe = calculate_sharpe_ratio(returns, risk_free_rate, annualization_factor)
            
            std_returns = np.std(returns, ddof=1)
            if std_returns == 0:
                return ToolResult.ok(
                    data={
                        "sharpe_ratio": 0.0,
                        "annual_return": 0.0,
                        "annual_volatility": 0.0,
                        "data_points": len(values)
                    }
                )
            
            annual_return = np.mean(returns) * annualization_factor
            annual_volatility = std_returns * np.sqrt(annualization_factor)
            excess_return = np.mean(returns - risk_free_rate / annualization_factor) * annualization_factor
            
            return ToolResult.ok(
                data={
                    "sharpe_ratio": round(float(sharpe), 2),
                    "annual_return": round(float(annual_return * 100), 2),
                    "annual_volatility": round(float(annual_volatility * 100), 2),
                    "excess_return": round(float(excess_return * 100), 2),
                    "data_points": len(values)
                }
            )
            
        except Exception as e:
            logger.error(f"计算夏普比率失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算夏普比率异常: {str(e)}")

@register_tool
class CalculateBetaTool(BaseTool):
    """
    计算Beta系数工具
    
    计算基金相对于基准的Beta系数
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.RISK_METRIC
    
    @property
    def name(self) -> str:
        return "calculate_beta"
    
    @property
    def description(self) -> str:
        return "计算Beta系数，衡量基金相对于基准指数的系统性风险"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "基金净值序列数组，按时间升序排列"
                },
                "benchmark_nav_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "基准指数净值序列数组，按时间升序排列"
                }
            },
            "required": ["fund_nav_values", "benchmark_nav_values"]
        }
    
    async def execute(
        self, 
        fund_nav_values: List[float], 
        benchmark_nav_values: List[float]
    ) -> ToolResult:
        """
        执行Beta系数计算
        
        Args:
            fund_nav_values: 基金净值序列
            benchmark_nav_values: 基准净值序列
            
        Returns:
            计算结果
        """
        try:
            fund_values = np.array([v for v in fund_nav_values if v > 0])
            benchmark_values = np.array([v for v in benchmark_nav_values if v > 0])
            
            if len(fund_values) < 2 or len(benchmark_values) < 2:
                return ToolResult.fail("净值数据不足，至少需要2个数据点")
            
            fund_returns = np.diff(fund_values) / fund_values[:-1]
            benchmark_returns = np.diff(benchmark_values) / benchmark_values[:-1]
            
            min_len = min(len(fund_returns), len(benchmark_returns))
            if min_len < 2:
                return ToolResult.fail("收益率数据不足")
            
            fund_returns = fund_returns[-min_len:]
            benchmark_returns = benchmark_returns[-min_len:]
            
            beta, correlation = calculate_beta(fund_returns, benchmark_returns)
            
            if beta is None:
                return ToolResult.ok(
                    data={
                        "beta": 1.0,
                        "correlation": 0.0,
                        "fund_volatility": round(float(np.std(fund_returns, ddof=1) * np.sqrt(252) * 100), 2),
                        "benchmark_volatility": 0.0,
                        "data_points": min_len
                    }
                )
            
            return ToolResult.ok(
                data={
                    "beta": round(float(beta), 2),
                    "correlation": round(float(correlation), 2),
                    "fund_volatility": round(float(np.std(fund_returns, ddof=1) * np.sqrt(252) * 100), 2),
                    "benchmark_volatility": round(float(np.std(benchmark_returns, ddof=1) * np.sqrt(252) * 100), 2),
                    "data_points": min_len
                }
            )
            
        except Exception as e:
            logger.error(f"计算Beta系数失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算Beta系数异常: {str(e)}")
