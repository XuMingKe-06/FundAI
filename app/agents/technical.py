"""
技术分析师智能体

负责均线系统分析、MACD指标解读、RSI指标分析、趋势判断
通过LLM进行综合技术分析和评分
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager


logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    """技术分析师智能体"""
    
    def __init__(self):
        super().__init__("technical", "技术分析师")
    
    def _calculate_ma(self, values: List[float], period: int) -> Optional[float]:
        """
        计算移动平均线
        
        Args:
            values: 净值数据列表（按时间升序排列）
            period: 移动平均周期
            
        Returns:
            移动平均值，数据不足时返回 None
        """
        if len(values) < period:
            return None
        recent_values = values[-period:]
        return sum(recent_values) / period
    
    def _calculate_macd(self, values: List[float]) -> Dict[str, Any]:
        """
        计算 MACD 指标（参数：12, 26, 9）
        
        MACD = EMA(12) - EMA(26)
        Signal = EMA(MACD, 9)
        Histogram = MACD - Signal
        
        Args:
            values: 净值数据列表（按时间升序排列）
            
        Returns:
            包含 macd, signal, histogram, signal_type 的字典
        """
        if len(values) < 26:
            return {
                "macd": None,
                "signal": None,
                "histogram": None,
                "signal_type": "数据不足"
            }
        
        def calculate_ema(data: List[float], period: int) -> List[float]:
            """计算指数移动平均"""
            ema = []
            multiplier = 2 / (period + 1)
            sma = sum(data[:period]) / period
            ema.append(sma)
            for i in range(period, len(data)):
                ema_value = (data[i] - ema[-1]) * multiplier + ema[-1]
                ema.append(ema_value)
            return ema
        
        ema_12 = calculate_ema(values, 12)
        ema_26 = calculate_ema(values, 26)
        
        macd_line = []
        for i in range(len(ema_26)):
            ema12_idx = i + (26 - 12)
            if ema12_idx < len(ema_12):
                macd_line.append(ema_12[ema12_idx] - ema_26[i])
        
        if len(macd_line) < 9:
            return {
                "macd": None,
                "signal": None,
                "histogram": None,
                "signal_type": "数据不足"
            }
        
        signal_line = calculate_ema(macd_line, 9)
        
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = current_macd - current_signal
        
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
        else:
            signal_type = "多头" if current_macd > current_signal else "空头"
        
        return {
            "macd": round(current_macd, 6),
            "signal": round(current_signal, 6),
            "histogram": round(current_histogram, 6),
            "signal_type": signal_type
        }
    
    def _calculate_rsi(self, values: List[float], period: int = 14) -> Optional[float]:
        """
        计算 RSI 指标
        
        RSI = 100 - 100 / (1 + RS)
        RS = 平均上涨幅度 / 平均下跌幅度
        
        Args:
            values: 净值数据列表（按时间升序排列）
            period: RSI 计算周期，默认14
            
        Returns:
            RSI 值（0-100），数据不足时返回 None
        """
        if len(values) < period + 1:
            return None
        
        changes = []
        for i in range(1, len(values)):
            changes.append(values[i] - values[i-1])
        
        recent_changes = changes[-(period):]
        
        gains = [c for c in recent_changes if c > 0]
        losses = [-c for c in recent_changes if c < 0]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_percentile(self, current_value: float, historical_values: List[float]) -> float:
        """
        计算当前值在历史数据中的分位数
        
        Args:
            current_value: 当前净值
            historical_values: 历史净值列表
            
        Returns:
            分位数（0-100）
        """
        if not historical_values:
            return 50.0
        
        count_below = sum(1 for v in historical_values if v < current_value)
        percentile = (count_below / len(historical_values)) * 100
        
        return round(percentile, 1)
    
    def _get_rsi_status(self, rsi: Optional[float]) -> str:
        """获取RSI状态描述"""
        if rsi is None:
            return "数据不足"
        if rsi < 30:
            return "超卖区间"
        elif rsi > 70:
            return "超买区间"
        elif 40 <= rsi <= 60:
            return "中性区间"
        else:
            return "中性偏强" if rsi > 50 else "中性偏弱"
    
    def _get_valuation_status(self, percentile: float) -> str:
        """获取估值状态描述"""
        if percentile < 20:
            return "低估区间"
        elif percentile > 80:
            return "高估区间"
        elif 30 <= percentile <= 50:
            return "合理偏低"
        elif 50 < percentile <= 70:
            return "合理偏高"
        else:
            return "合理区间"
    
    def _get_ma_trend(self, current_nav: float, ma20: Optional[float], 
                       ma60: Optional[float], ma120: Optional[float]) -> str:
        """获取均线趋势描述"""
        if ma20 and ma60 and ma120:
            if current_nav > ma20 > ma60 > ma120:
                return "多头排列"
            elif current_nav < ma20 < ma60 < ma120:
                return "空头排列"
        return "震荡"
    
    async def _prepare_technical_context(self, fund_code: str) -> Dict[str, Any]:
        """
        准备技术分析上下文数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含技术指标数据的上下文字典
        """
        await self.add_thinking("正在获取基金净值历史数据...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * 3)
        
        nav_history = await datasource_manager.get_nav_history(
            fund_code=fund_code,
            start_date=start_date,
            end_date=end_date
        )

        # 保存完整净值历史到实例属性，供 save_decision_report 构建走势图使用
        self._full_nav_history = nav_history
        
        if not nav_history or len(nav_history) < 120:
            await self.add_thinking(
                f"净值数据不足（共{len(nav_history) if nav_history else 0}条），无法进行完整技术分析"
            )
            return {
                "nav_data": {
                    "current_nav": None,
                    "nav_date": None,
                    "data_period": len(nav_history) if nav_history else 0,
                    "min_nav": None,
                    "max_nav": None,
                    "recent_nav": []
                },
                "indicators": {
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                    "ma_trend": "数据不足",
                    "macd_value": None,
                    "macd_signal": None,
                    "macd_histogram": None,
                    "macd_signal_type": "数据不足",
                    "rsi_14": None,
                    "rsi_status": "数据不足",
                    "valuation_percentile": None,
                    "valuation_status": "数据不足"
                },
                "data_sufficient": False
            }
        
        await self.add_thinking(f"获取到近3年净值数据，共{len(nav_history)}个交易日")
        
        nav_values = []
        for item in nav_history:
            nav_value = item.get("nav") or item.get("unit_nav")
            if nav_value is not None:
                nav_values.append(float(nav_value))
        
        if len(nav_values) < 120:
            await self.add_thinking(f"有效净值数据不足（共{len(nav_values)}条）")
            return {
                "nav_data": {
                    "current_nav": nav_values[-1] if nav_values else None,
                    "nav_date": nav_history[-1].get("date") if nav_history else None,
                    "data_period": len(nav_values),
                    "min_nav": min(nav_values) if nav_values else None,
                    "max_nav": max(nav_values) if nav_values else None,
                    "recent_nav": []
                },
                "indicators": {
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                    "ma_trend": "数据不足",
                    "macd_value": None,
                    "macd_signal": None,
                    "macd_histogram": None,
                    "macd_signal_type": "数据不足",
                    "rsi_14": None,
                    "rsi_status": "数据不足",
                    "valuation_percentile": None,
                    "valuation_status": "数据不足"
                },
                "data_sufficient": False
            }
        
        current_nav = nav_values[-1]
        
        await self.add_thinking("正在计算均线系统...")
        ma20 = self._calculate_ma(nav_values, 20)
        ma60 = self._calculate_ma(nav_values, 60)
        ma120 = self._calculate_ma(nav_values, 120)
        ma_trend = self._get_ma_trend(current_nav, ma20, ma60, ma120)
        
        await self.add_thinking(
            f"MA20={round(ma20, 4) if ma20 else 'N/A'}, "
            f"MA60={round(ma60, 4) if ma60 else 'N/A'}, "
            f"MA120={round(ma120, 4) if ma120 else 'N/A'}，均线呈{ma_trend}"
        )
        
        await self.add_thinking("正在计算MACD指标...")
        macd_result = self._calculate_macd(nav_values)
        
        await self.add_thinking(
            f"MACD信号: {macd_result['signal_type']}, "
            f"柱状图: {round(macd_result['histogram'], 4) if macd_result['histogram'] else 'N/A'}"
        )
        
        await self.add_thinking("正在计算RSI指标...")
        rsi = self._calculate_rsi(nav_values, 14)
        rsi_status = self._get_rsi_status(rsi)
        
        await self.add_thinking(f"RSI(14)={rsi if rsi else 'N/A'}，处于{rsi_status}")
        
        await self.add_thinking("正在计算估值分位数...")
        percentile = self._calculate_percentile(current_nav, nav_values)
        valuation_status = self._get_valuation_status(percentile)
        
        await self.add_thinking(f"当前估值处于近3年{percentile}%分位，属于{valuation_status}")
        
        recent_nav = []
        for item in nav_history[-10:]:
            nav_val = item.get("nav") or item.get("unit_nav")
            change_pct = item.get("change_pct") or item.get("pct_change")
            recent_nav.append({
                "date": item.get("date"),
                "nav": round(float(nav_val), 4) if nav_val else None,
                "change_pct": round(float(change_pct), 2) if change_pct else None
            })
        
        return {
            "nav_data": {
                "current_nav": round(current_nav, 4),
                "nav_date": nav_history[-1].get("date"),
                "data_period": len(nav_values),
                "min_nav": round(min(nav_values), 4),
                "max_nav": round(max(nav_values), 4),
                "recent_nav": recent_nav
            },
            "indicators": {
                "ma20": round(ma20, 4) if ma20 else None,
                "ma60": round(ma60, 4) if ma60 else None,
                "ma120": round(ma120, 4) if ma120 else None,
                "ma_trend": ma_trend,
                "macd_value": macd_result.get("macd"),
                "macd_signal": macd_result.get("signal"),
                "macd_histogram": macd_result.get("histogram"),
                "macd_signal_type": macd_result.get("signal_type"),
                "rsi_14": rsi,
                "rsi_status": rsi_status,
                "valuation_percentile": percentile,
                "valuation_status": valuation_status
            },
            "data_sufficient": True
        }
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技术分析
        
        通过LLM进行综合技术分析和评分
        
        Args:
            fund_code: 基金代码
            context: 上下文信息
            
        Returns:
            分析结果字典
        """
        try:
            technical_context = await self._prepare_technical_context(fund_code)
            
            analysis_context = {
                **context,
                "nav_data": technical_context.get("nav_data", {}),
                "indicators": technical_context.get("indicators", {}),
                "data_sufficient": technical_context.get("data_sufficient", False)
            }
            
            result = await self.run_llm_analysis(
                fund_code=fund_code,
                context=analysis_context,
                use_rag=True,
                use_tools=True
            )
            
            return self.to_dict()
            
        except Exception as e:
            logger.error(f"技术分析异常: {e}", exc_info=True)
            await self.add_thinking(f"技术分析过程中发生错误: {str(e)}")
            self.score = 3.0
            self.summary = "技术分析异常，请稍后重试"
            self.details = {
                "trend_direction": "未知",
                "ma20": None,
                "ma60": None,
                "ma120": None,
                "macd_signal": "分析异常",
                "macd_value": None,
                "macd_histogram": None,
                "rsi_14": None,
                "valuation_percentile": None,
                "prediction_15d": {
                    "direction": "无法预测",
                    "target_low": None,
                    "target_high": None
                },
                "current_nav": None,
                "data_points": 0,
                "error": str(e)
            }
            return self.to_dict()
