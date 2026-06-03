"""
技术指标计算工具

提供移动平均线、MACD、RSI、估值分位数等技术指标计算功能
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from app.agents.tools.base import (
    BaseTool, 
    ToolResult, 
    ToolCategory,
    register_tool
)
from app.core.calculations import calculate_ma, calculate_ma_slope, calculate_macd, calculate_rsi, calculate_percentile
from app.core.calculations.ema import calculate_ema

@register_tool
class CalculateMATool(BaseTool):
    """
    计算移动平均线工具
    
    计算简单移动平均线（SMA），支持多种周期
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR
    
    @property
    def name(self) -> str:
        return "calculate_ma"
    
    @property
    def description(self) -> str:
        return "计算移动平均线（MA），支持自定义周期，返回MA值和趋势判断"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列"
                },
                "period": {
                    "type": "integer",
                    "description": "移动平均周期，如 5、10、20、60、120",
                    "default": 20
                }
            },
            "required": ["values"]
        }
    
    async def execute(self, values: List[float], period: int = 20) -> ToolResult:
        """
        执行移动平均线计算
        
        Args:
            values: 净值数据列表（按时间升序）
            period: 移动平均周期
            
        Returns:
            包含MA计算结果的 ToolResult
        """
        try:
            if not values or len(values) < period:
                return ToolResult.fail(
                    f"数据不足，需要至少 {period} 个数据点",
                    metadata={"data_points": len(values) if values else 0, "period": period}
                )
            
            ma_value = calculate_ma(values, period)
            if ma_value is None:
                return ToolResult.fail(
                    f"数据不足，需要至少 {period} 个数据点",
                    metadata={"data_points": len(values) if values else 0, "period": period}
                )
            
            current_value = values[-1]
            prev_value = values[-2] if len(values) > 1 else values[-1]
            
            if current_value > ma_value:
                position = "上方"
                trend = "偏强"
            elif current_value < ma_value:
                position = "下方"
                trend = "偏弱"
            else:
                position = "附近"
                trend = "中性"
            
            ma_slope = calculate_ma_slope(values, period)
            if ma_slope is None:
                ma_trend = "数据不足"
            elif ma_slope > 0:
                ma_trend = "上升"
            elif ma_slope < 0:
                ma_trend = "下降"
            else:
                ma_trend = "平稳"
            
            return ToolResult.ok(
                data={
                    "ma_value": round(ma_value, 4),
                    "period": period,
                    "current_position": position,
                    "trend": trend,
                    "ma_trend": ma_trend,
                    "distance_percent": round(abs(current_value - ma_value) / ma_value * 100, 2)
                },
                metadata={
                    "data_points": len(values),
                    "period": period
                }
            )
            
        except Exception as e:
            logger.error(f"计算移动平均线失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算移动平均线异常: {str(e)}")

@register_tool
class CalculateMACDTool(BaseTool):
    """
    计算 MACD 指标工具
    
    计算指数平滑异同移动平均线（MACD），包含 DIF、DEA、MACD 柱状图
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR
    
    @property
    def name(self) -> str:
        return "calculate_macd"
    
    @property
    def description(self) -> str:
        return "计算MACD指标（12,26,9参数），返回DIF、DEA、MACD柱状图及信号判断"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列，至少需要26个数据点"
                },
                "fast_period": {
                    "type": "integer",
                    "description": "快线周期，默认12",
                    "default": 12
                },
                "slow_period": {
                    "type": "integer",
                    "description": "慢线周期，默认26",
                    "default": 26
                },
                "signal_period": {
                    "type": "integer",
                    "description": "信号线周期，默认9",
                    "default": 9
                }
            },
            "required": ["values"]
        }
    
    async def execute(
        self, 
        values: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> ToolResult:
        """
        执行 MACD 指标计算
        
        Args:
            values: 净值数据列表（按时间升序）
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            包含MACD计算结果的 ToolResult
        """
        try:
            if not values or len(values) < slow_period:
                return ToolResult.fail(
                    f"数据不足，需要至少 {slow_period} 个数据点",
                    metadata={"data_points": len(values) if values else 0}
                )
            
            ema_fast = calculate_ema(values, fast_period)
            ema_slow = calculate_ema(values, slow_period)
            
            if len(ema_fast) < len(ema_slow):
                return ToolResult.fail(
                    "EMA计算结果不匹配",
                    metadata={"ema_fast_len": len(ema_fast), "ema_slow_len": len(ema_slow)}
                )
            
            offset = len(ema_fast) - len(ema_slow)
            macd_line = []
            for i in range(len(ema_slow)):
                if offset + i < len(ema_fast):
                    macd_line.append(ema_fast[offset + i] - ema_slow[i])
            
            if len(macd_line) < signal_period:
                return ToolResult.fail(
                    f"MACD线数据不足，无法计算信号线",
                    metadata={"macd_line_len": len(macd_line)}
                )
            
            signal_line = calculate_ema(macd_line, signal_period)
            
            if not signal_line:
                return ToolResult.fail("信号线计算失败")
            
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            current_histogram = current_macd - current_signal
            
            signal_type = "震荡"
            if len(macd_line) >= 2 and len(signal_line) >= 2:
                prev_macd = macd_line[-2]
                prev_signal = signal_line[-2]
                
                if prev_macd <= prev_signal and current_macd > current_signal:
                    signal_type = "金叉"
                elif prev_macd >= prev_signal and current_macd < current_signal:
                    signal_type = "死叉"
                elif current_macd > current_signal:
                    signal_type = "多头"
                else:
                    signal_type = "空头"
            
            histogram_trend = "放大" if abs(current_histogram) > abs(macd_line[-2] - signal_line[-2]) else "缩小"
            
            return ToolResult.ok(
                data={
                    "dif": round(current_macd, 6),
                    "dea": round(current_signal, 6),
                    "macd_histogram": round(current_histogram * 2, 6),
                    "signal_type": signal_type,
                    "histogram_trend": histogram_trend,
                    "is_golden_cross": signal_type == "金叉",
                    "is_death_cross": signal_type == "死叉"
                },
                metadata={
                    "data_points": len(values),
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period
                }
            )
            
        except Exception as e:
            logger.error(f"计算MACD指标失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算MACD指标异常: {str(e)}")

@register_tool
class CalculateRSITool(BaseTool):
    """
    计算 RSI 指标工具
    
    计算相对强弱指标（RSI），用于判断超买超卖状态
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR
    
    @property
    def name(self) -> str:
        return "calculate_rsi"
    
    @property
    def description(self) -> str:
        return "计算RSI相对强弱指标，返回RSI值和超买超卖状态判断"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "净值数据列表，按时间升序排列"
                },
                "period": {
                    "type": "integer",
                    "description": "RSI计算周期，默认14",
                    "default": 14
                }
            },
            "required": ["values"]
        }
    
    async def execute(self, values: List[float], period: int = 14) -> ToolResult:
        """
        执行 RSI 指标计算
        
        Args:
            values: 净值数据列表（按时间升序）
            period: RSI 周期
            
        Returns:
            包含RSI计算结果的 ToolResult
        """
        try:
            if not values or len(values) < period + 1:
                return ToolResult.fail(
                    f"数据不足，需要至少 {period + 1} 个数据点",
                    metadata={"data_points": len(values) if values else 0, "period": period}
                )
            
            rsi_value = calculate_rsi(values, period)
            if rsi_value is None:
                return ToolResult.fail(
                    f"数据不足，需要至少 {period + 1} 个数据点",
                    metadata={"data_points": len(values) if values else 0, "period": period}
                )
            
            if rsi_value < 30:
                status = "超卖"
                signal = "可能反弹"
            elif rsi_value > 70:
                status = "超买"
                signal = "可能回调"
            elif 40 <= rsi_value <= 60:
                status = "中性"
                signal = "观望"
            elif rsi_value > 60:
                status = "偏强"
                signal = "保持关注"
            else:
                status = "偏弱"
                signal = "保持关注"
            
            return ToolResult.ok(
                data={
                    "rsi_value": round(rsi_value, 2),
                    "period": period,
                    "status": status,
                    "signal": signal,
                    "is_oversold": rsi_value < 30,
                    "is_overbought": rsi_value > 70
                },
                metadata={
                    "data_points": len(values),
                    "period": period
                }
            )
            
        except Exception as e:
            logger.error(f"计算RSI指标失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算RSI指标异常: {str(e)}")

@register_tool
class CalculatePercentileTool(BaseTool):
    """
    计算估值分位数工具
    
    计算当前值在历史数据中的分位数位置
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.TECHNICAL_INDICATOR
    
    @property
    def name(self) -> str:
        return "calculate_percentile"
    
    @property
    def description(self) -> str:
        return "计算当前净值在历史数据中的分位数，用于判断估值水平"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_value": {
                    "type": "number",
                    "description": "当前净值"
                },
                "historical_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "历史净值数据列表"
                }
            },
            "required": ["current_value", "historical_values"]
        }
    
    async def execute(
        self, 
        current_value: float, 
        historical_values: List[float]
    ) -> ToolResult:
        """
        执行估值分位数计算
        
        Args:
            current_value: 当前净值
            historical_values: 历史净值列表
            
        Returns:
            包含分位数计算结果的 ToolResult
        """
        try:
            if not historical_values:
                return ToolResult.fail("历史数据为空")
            
            percentile = calculate_percentile(current_value, historical_values)
            
            if percentile < 20:
                valuation_level = "低估"
                suggestion = "具有投资价值"
            elif percentile < 40:
                valuation_level = "合理偏低"
                suggestion = "可考虑配置"
            elif percentile < 60:
                valuation_level = "合理"
                suggestion = "正常持有"
            elif percentile < 80:
                valuation_level = "合理偏高"
                suggestion = "谨慎追高"
            else:
                valuation_level = "高估"
                suggestion = "注意风险"
            
            max_value = max(historical_values)
            min_value = min(historical_values)
            avg_value = sum(historical_values) / len(historical_values)
            
            return ToolResult.ok(
                data={
                    "percentile": round(percentile, 1),
                    "valuation_level": valuation_level,
                    "suggestion": suggestion,
                    "current_value": round(current_value, 4),
                    "max_value": round(max_value, 4),
                    "min_value": round(min_value, 4),
                    "avg_value": round(avg_value, 4),
                    "distance_to_max": round((max_value - current_value) / current_value * 100, 2),
                    "distance_to_min": round((current_value - min_value) / current_value * 100, 2)
                },
                metadata={
                    "data_points": len(historical_values)
                }
            )
            
        except Exception as e:
            logger.error(f"计算估值分位数失败: {e}", exc_info=True)
            return ToolResult.fail(f"计算估值分位数异常: {str(e)}")
