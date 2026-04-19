"""
技术分析师智能体
"""
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
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
        # 取最近 period 个数据计算平均值
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
        
        # 计算 EMA
        def calculate_ema(data: List[float], period: int) -> List[float]:
            """计算指数移动平均"""
            ema = []
            multiplier = 2 / (period + 1)
            # 第一个 EMA 值使用简单平均
            sma = sum(data[:period]) / period
            ema.append(sma)
            # 后续使用 EMA 公式
            for i in range(period, len(data)):
                ema_value = (data[i] - ema[-1]) * multiplier + ema[-1]
                ema.append(ema_value)
            return ema
        
        # 计算 EMA(12) 和 EMA(26)
        ema_12 = calculate_ema(values, 12)
        ema_26 = calculate_ema(values, 26)
        
        # 计算 MACD 线（DIF）
        # EMA(12) 从第12个数据开始，EMA(26) 从第26个数据开始
        # MACD 从第26个数据开始有值
        macd_line = []
        for i in range(len(ema_26)):
            # ema_12 的索引需要调整，因为它从第12个开始
            ema12_idx = i + (26 - 12)  # 26 - 12 = 14 的偏移
            if ema12_idx < len(ema_12):
                macd_line.append(ema_12[ema12_idx] - ema_26[i])
        
        if len(macd_line) < 9:
            return {
                "macd": None,
                "signal": None,
                "histogram": None,
                "signal_type": "数据不足"
            }
        
        # 计算信号线（DEA）- MACD 的 9 日 EMA
        signal_line = calculate_ema(macd_line, 9)
        
        # 获取最新值
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = current_macd - current_signal
        
        # 判断信号类型
        if len(macd_line) >= 2 and len(signal_line) >= 2:
            prev_macd = macd_line[-2]
            prev_signal = signal_line[-2]
            
            # 金叉：MACD 从下向上穿过信号线
            if prev_macd <= prev_signal and current_macd > current_signal:
                signal_type = "金叉"
            # 死叉：MACD 从上向下穿过信号线
            elif prev_macd >= prev_signal and current_macd < current_signal:
                signal_type = "死叉"
            # 上升趋势
            elif current_macd > current_signal:
                signal_type = "多头"
            # 下降趋势
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
        
        # 计算价格变化
        changes = []
        for i in range(1, len(values)):
            changes.append(values[i] - values[i-1])
        
        # 取最近 period 个变化值
        recent_changes = changes[-(period):]
        
        # 计算上涨和下跌幅度
        gains = [c for c in recent_changes if c > 0]
        losses = [-c for c in recent_changes if c < 0]
        
        # 计算平均上涨和下跌幅度
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        # 计算 RS 和 RSI
        if avg_loss == 0:
            return 100.0  # 没有下跌，RSI 为 100
        
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
            return 50.0  # 默认返回中位数
        
        # 计算小于当前值的数量
        count_below = sum(1 for v in historical_values if v < current_value)
        percentile = (count_below / len(historical_values)) * 100
        
        return round(percentile, 1)
    
    def _calculate_score(
        self,
        ma_trend: str,
        macd_signal: str,
        rsi: float,
        percentile: float
    ) -> float:
        """
        根据技术指标计算综合评分
        
        Args:
            ma_trend: 均线趋势（"多头排列"/"空头排列"/"震荡"）
            macd_signal: MACD 信号
            rsi: RSI 值
            percentile: 估值分位数
            
        Returns:
            评分（1-5分）
        """
        score = 3.0  # 基础分
        
        # 均线趋势评分
        if ma_trend == "多头排列":
            score += 0.5
        elif ma_trend == "空头排列":
            score -= 0.5
        
        # MACD 信号评分
        if macd_signal == "金叉":
            score += 0.5
        elif macd_signal == "死叉":
            score -= 0.5
        elif macd_signal == "多头":
            score += 0.2
        elif macd_signal == "空头":
            score -= 0.2
        
        # RSI 评分（中性区域 40-60 不加减分）
        if rsi < 30:
            score += 0.3  # 超卖，可能反弹
        elif rsi > 70:
            score -= 0.3  # 超买，可能回调
        elif 40 <= rsi <= 60:
            score += 0.1  # 中性偏强
        
        # 估值分位数评分
        if percentile < 20:
            score += 0.4  # 低估值
        elif percentile > 80:
            score -= 0.4  # 高估值
        elif 30 <= percentile <= 50:
            score += 0.2  # 合理偏低
        
        # 限制评分范围 1-5
        return max(1.0, min(5.0, round(score, 1)))
    
    def _generate_prediction(
        self,
        current_nav: float,
        ma20: float,
        ma60: float,
        macd_signal: str,
        rsi: float
    ) -> Dict[str, Any]:
        """
        生成未来15天走势预测
        
        Args:
            current_nav: 当前净值
            ma20: 20日均线
            ma60: 60日均线
            macd_signal: MACD 信号
            rsi: RSI 值
            
        Returns:
            预测结果字典
        """
        # 根据技术指标判断趋势方向
        bullish_signals = 0
        bearish_signals = 0
        
        # 均线判断
        if current_nav > ma20 > ma60:
            bullish_signals += 1
        elif current_nav < ma20 < ma60:
            bearish_signals += 1
        
        # MACD 判断
        if macd_signal in ["金叉", "多头"]:
            bullish_signals += 1
        elif macd_signal in ["死叉", "空头"]:
            bearish_signals += 1
        
        # RSI 判断
        if rsi < 30:
            bullish_signals += 1  # 超卖可能反弹
        elif rsi > 70:
            bearish_signals += 1  # 超买可能回调
        
        # 确定方向
        if bullish_signals > bearish_signals:
            direction = "震荡上行"
            volatility = 0.03  # 3% 波动
        elif bearish_signals > bullish_signals:
            direction = "震荡下行"
            volatility = 0.03
        else:
            direction = "横盘震荡"
            volatility = 0.02
        
        # 计算目标区间
        if bullish_signals > bearish_signals:
            target_low = current_nav * (1 + 0.01)
            target_high = current_nav * (1 + volatility + 0.01)
        elif bearish_signals > bullish_signals:
            target_low = current_nav * (1 - volatility - 0.01)
            target_high = current_nav * (1 - 0.01)
        else:
            target_low = current_nav * (1 - volatility / 2)
            target_high = current_nav * (1 + volatility / 2)
        
        return {
            "direction": direction,
            "target_low": round(target_low, 4),
            "target_high": round(target_high, 4)
        }
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技术分析
        
        Args:
            fund_code: 基金代码
            context: 上下文信息
            
        Returns:
            分析结果字典
        """
        try:
            # 获取净值历史数据（近3年）
            self.add_thinking("正在获取基金净值历史数据...")
            end_date = date.today()
            start_date = end_date - timedelta(days=365 * 3)
            
            nav_history = await datasource_manager.get_nav_history(
                fund_code=fund_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if not nav_history or len(nav_history) < 120:
                # 数据不足，返回默认结果
                self.add_thinking(f"净值数据不足（共{len(nav_history) if nav_history else 0}条），无法进行完整技术分析")
                self.score = 3.0
                self.summary = "数据不足，无法进行完整技术分析"
                self.details = {
                    "trend_direction": "未知",
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                    "macd_signal": "数据不足",
                    "rsi_14": None,
                    "valuation_percentile": None,
                    "prediction_15d": {
                        "direction": "无法预测",
                        "target_low": None,
                        "target_high": None
                    },
                    "data_points": len(nav_history) if nav_history else 0
                }
                return self.to_dict()
            
            self.add_thinking(f"获取到近3年净值数据，共{len(nav_history)}个交易日")
            
            # 提取净值数据（按日期升序排列）
            nav_values = []
            for item in nav_history:
                nav_value = item.get("nav") or item.get("unit_nav")
                if nav_value is not None:
                    nav_values.append(float(nav_value))
            
            if len(nav_values) < 120:
                self.add_thinking(f"有效净值数据不足（共{len(nav_values)}条）")
                self.score = 3.0
                self.summary = "有效数据不足，无法进行完整技术分析"
                self.details = {
                    "trend_direction": "未知",
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                    "macd_signal": "数据不足",
                    "rsi_14": None,
                    "valuation_percentile": None,
                    "prediction_15d": {
                        "direction": "无法预测",
                        "target_low": None,
                        "target_high": None
                    },
                    "data_points": len(nav_values)
                }
                return self.to_dict()
            
            current_nav = nav_values[-1]
            
            # 计算均线系统
            self.add_thinking("正在计算均线系统...")
            ma20 = self._calculate_ma(nav_values, 20)
            ma60 = self._calculate_ma(nav_values, 60)
            ma120 = self._calculate_ma(nav_values, 120)
            
            # 判断均线趋势
            if ma20 and ma60 and ma120:
                if current_nav > ma20 > ma60 > ma120:
                    ma_trend = "多头排列"
                elif current_nav < ma20 < ma60 < ma120:
                    ma_trend = "空头排列"
                else:
                    ma_trend = "震荡"
                self.add_thinking(
                    f"MA20={round(ma20, 4)}, MA60={round(ma60, 4)}, MA120={round(ma120, 4) if ma120 else 'N/A'}，"
                    f"均线呈{ma_trend}"
                )
            else:
                ma_trend = "震荡"
                self.add_thinking(f"MA20={round(ma20, 4) if ma20 else 'N/A'}, MA60={round(ma60, 4) if ma60 else 'N/A'}")
            
            # 计算 MACD 指标
            self.add_thinking("正在计算MACD指标...")
            macd_result = self._calculate_macd(nav_values)
            macd_signal = macd_result["signal_type"]
            self.add_thinking(
                f"MACD{'金叉' if macd_signal == '金叉' else '死叉' if macd_signal == '死叉' else macd_signal}"
                f"，柱状图{'加速向上' if macd_result['histogram'] and macd_result['histogram'] > 0 else '走弱'}"
            )
            
            # 计算 RSI 指标
            self.add_thinking("正在计算RSI指标...")
            rsi = self._calculate_rsi(nav_values, 14)
            if rsi is not None:
                if rsi < 30:
                    rsi_status = "超卖区间"
                elif rsi > 70:
                    rsi_status = "超买区间"
                elif 40 <= rsi <= 60:
                    rsi_status = "中性区间"
                else:
                    rsi_status = "中性偏强" if rsi > 50 else "中性偏弱"
                self.add_thinking(f"RSI(14)={rsi}，处于{rsi_status}")
            else:
                self.add_thinking("RSI计算数据不足")
            
            # 计算估值分位数
            self.add_thinking("正在计算估值分位数...")
            percentile = self._calculate_percentile(current_nav, nav_values)
            if percentile < 20:
                percentile_status = "低估区间"
            elif percentile > 80:
                percentile_status = "高估区间"
            elif 30 <= percentile <= 50:
                percentile_status = "合理偏低"
            elif 50 < percentile <= 70:
                percentile_status = "合理偏高"
            else:
                percentile_status = "合理区间"
            self.add_thinking(f"当前估值处于近3年{percentile}%分位，属于{percentile_status}")
            
            # 生成走势预测
            self.add_thinking("正在进行走势预测...")
            prediction = self._generate_prediction(
                current_nav=current_nav,
                ma20=ma20 or current_nav,
                ma60=ma60 or current_nav,
                macd_signal=macd_signal,
                rsi=rsi or 50
            )
            self.add_thinking(
                f"预测未来15天走势：{prediction['direction']}，"
                f"目标区间{prediction['target_low']}-{prediction['target_high']}"
            )
            
            # 计算综合评分
            score = self._calculate_score(
                ma_trend=ma_trend,
                macd_signal=macd_signal,
                rsi=rsi or 50,
                percentile=percentile
            )
            
            # 生成摘要
            summary_parts = []
            if ma_trend == "多头排列":
                summary_parts.append("趋势向上")
            elif ma_trend == "空头排列":
                summary_parts.append("趋势向下")
            else:
                summary_parts.append("趋势震荡")
            
            if rsi is not None:
                if rsi < 30:
                    summary_parts.append("RSI超卖")
                elif rsi > 70:
                    summary_parts.append("RSI超买")
                else:
                    summary_parts.append("RSI中性")
            
            summary_parts.append(percentile_status)
            
            self.score = score
            self.summary = "，".join(summary_parts)
            
            self.details = {
                "trend_direction": "上升" if ma_trend == "多头排列" else "下降" if ma_trend == "空头排列" else "震荡",
                "ma20": round(ma20, 4) if ma20 else None,
                "ma60": round(ma60, 4) if ma60 else None,
                "ma120": round(ma120, 4) if ma120 else None,
                "macd_signal": macd_signal,
                "macd_value": macd_result.get("macd"),
                "macd_histogram": macd_result.get("histogram"),
                "rsi_14": rsi,
                "valuation_percentile": percentile,
                "prediction_15d": prediction,
                "current_nav": round(current_nav, 4),
                "data_points": len(nav_values)
            }
            
            self.add_thinking(f"综合评估：技术面评分{self.score}分。{self.summary}。")
            
            return self.to_dict()
            
        except Exception as e:
            logger.error(f"技术分析异常: {e}", exc_info=True)
            self.add_thinking(f"技术分析过程中发生错误: {str(e)}")
            self.score = 3.0
            self.summary = "技术分析异常，请稍后重试"
            self.details = {
                "trend_direction": "未知",
                "ma20": None,
                "ma60": None,
                "ma120": None,
                "macd_signal": "分析异常",
                "rsi_14": None,
                "valuation_percentile": None,
                "prediction_15d": {
                    "direction": "无法预测",
                    "target_low": None,
                    "target_high": None
                },
                "error": str(e)
            }
            return self.to_dict()
