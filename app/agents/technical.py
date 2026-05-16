from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager
from app.core.calculations import (
    calculate_ma, calculate_ma_slope, calculate_macd,
    calculate_rsi, calculate_percentile, calculate_bollinger_bands,
    calculate_kdj_from_nav, calculate_support_resistance
)
from app.core.data_provenance import annotate_data_source


logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__("technical", "技术分析师")

    def _get_rsi_status(self, rsi: Optional[float]) -> str:
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
        if ma20 and ma60 and ma120:
            if current_nav > ma20 > ma60 > ma120:
                return "多头排列"
            elif current_nav < ma20 < ma60 < ma120:
                return "空头排列"
        return "震荡"

    async def _prepare_technical_context(self, fund_code: str) -> Dict[str, Any]:
        await self.add_thinking("正在获取基金净值历史数据...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * 3)
        
        nav_history = await datasource_manager.get_nav_history(
            fund_code=fund_code,
            start_date=start_date,
            end_date=end_date
        )

        from app.core.data_quality import validate_nav_history

        quality_report = validate_nav_history(nav_history)
        if quality_report.has_warnings:
            for w in quality_report.warnings:
                await self.add_thinking(f"数据质量警告: {w['message']}")

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
                    "valuation_status": "数据不足",
                    "bollinger": None,
                    "kdj": None,
                    "support_resistance": None,
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
                    "valuation_status": "数据不足",
                    "bollinger": None,
                    "kdj": None,
                    "support_resistance": None,
                },
                "data_sufficient": False
            }
        
        current_nav = nav_values[-1]
        
        await self.add_thinking("正在计算均线系统...")
        ma20 = calculate_ma(nav_values, 20)
        ma60 = calculate_ma(nav_values, 60)
        ma120 = calculate_ma(nav_values, 120)
        ma_trend = self._get_ma_trend(current_nav, ma20, ma60, ma120)
        
        await self.add_thinking(
            f"MA20={round(ma20, 4) if ma20 else 'N/A'}, "
            f"MA60={round(ma60, 4) if ma60 else 'N/A'}, "
            f"MA120={round(ma120, 4) if ma120 else 'N/A'}，均线呈{ma_trend}"
        )
        
        await self.add_thinking("正在计算MACD指标...")
        macd_result = calculate_macd(nav_values)
        
        await self.add_thinking(
            f"MACD信号: {macd_result['signal_type']}, "
            f"柱状图: {round(macd_result['histogram'], 4) if macd_result['histogram'] else 'N/A'}"
        )
        
        await self.add_thinking("正在计算RSI指标...")
        rsi = calculate_rsi(nav_values, 14)
        rsi_status = self._get_rsi_status(rsi)
        
        await self.add_thinking(f"RSI(14)={rsi if rsi else 'N/A'}，处于{rsi_status}")
        
        await self.add_thinking("正在计算估值分位数...")
        percentile = calculate_percentile(current_nav, nav_values)
        valuation_status = self._get_valuation_status(percentile)
        
        await self.add_thinking(f"当前估值处于近3年{percentile}%分位，属于{valuation_status}")

        await self.add_thinking("正在计算布林带...")
        bollinger = calculate_bollinger_bands(nav_values, 20, 2.0)
        if bollinger.get("data_sufficient", False):
            await self.add_thinking(
                f"布林带: 上轨={bollinger['upper']}, 中轨={bollinger['middle']}, "
                f"下轨={bollinger['lower']}，信号: {bollinger['signal']}"
            )

        await self.add_thinking("正在计算KDJ指标...")
        kdj = calculate_kdj_from_nav(nav_values, 9, 3, 3)
        if kdj.get("data_sufficient", False):
            await self.add_thinking(
                f"KDJ: K={kdj['k']}, D={kdj['d']}, J={kdj['j']}，信号: {kdj['signal']}"
            )

        await self.add_thinking("正在识别支撑位和阻力位...")
        sr = calculate_support_resistance(nav_values, 3, 20)
        if sr.get("data_sufficient", False):
            await self.add_thinking(
                f"支撑位: {sr['support_levels']}, 阻力位: {sr['resistance_levels']}，"
                f"当前位置: {sr['current_position']}"
            )
        
        recent_nav = []
        for item in nav_history[-10:]:
            nav_val = item.get("nav") or item.get("unit_nav")
            change_pct = item.get("change_pct") or item.get("pct_change")
            recent_nav.append({
                "date": item.get("date"),
                "nav": round(float(nav_val), 4) if nav_val else None,
                "change_pct": round(float(change_pct), 2) if change_pct else None
            })
        
        result = {
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
                "valuation_status": valuation_status,
                "bollinger": bollinger if bollinger.get("data_sufficient") else None,
                "kdj": kdj if kdj.get("data_sufficient") else None,
                "support_resistance": sr if sr.get("data_sufficient") else None,
            },
            "data_sufficient": True
        }

        result = annotate_data_source(result, "technical_indicators")

        return result
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
            self.score = None
            self.data_sufficient = False
            self.confidence = 1
            self.data_sufficiency = "insufficient"
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
