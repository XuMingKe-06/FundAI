from typing import Dict, Any, List, Optional, Tuple
from datetime import date, timedelta
import numpy as np
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager
from app.core.calculations import (
    calculate_volatility, calculate_max_drawdown, calculate_current_drawdown,
    calculate_sharpe_ratio, calculate_sortino_ratio, calculate_calmar_ratio,
    calculate_beta, calculate_var, calculate_cvar, calculate_downside_risk,
    stress_test
)
from app.core.data_quality import validate_nav_history, validate_holdings, check_data_timeliness
from app.core.data_provenance import annotate_data_source, annotate_stale_data

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("risk", "风险分析师")
    
    def _calculate_concentration_risk(
        self, 
        holdings: Optional[Dict[str, Any]]
    ) -> Tuple[float, float, int, List[str]]:
        alerts = []
        top10_concentration = 0.0
        single_industry_max = 0.0
        industry_count = 0
        
        if not holdings:
            alerts.append("无法获取持仓数据，集中度风险未知")
            return top10_concentration, single_industry_max, industry_count, alerts
        
        stock_list = holdings.get("stock_list", [])
        if stock_list:
            top10_stocks = stock_list[:10]
            top10_concentration = sum(
                float(s.get("proportion", 0)) for s in top10_stocks
            )
            
            if top10_concentration > 60:
                alerts.append(f"前十大持仓占比{top10_concentration:.1f}%，集中度较高")
        
        industry_list = holdings.get("industry_list", [])
        if industry_list:
            industry_count = len(industry_list)
            proportions = [
                float(i.get("proportion", 0)) for i in industry_list
            ]
            if proportions:
                single_industry_max = max(proportions)
                
                if single_industry_max > 30:
                    alerts.append(f"单一行业占比{single_industry_max:.1f}%，行业集中度风险较高")
        
        if not alerts:
            if top10_concentration > 0 or single_industry_max > 0:
                alerts.append("持仓集中度处于合理水平")
        
        return round(top10_concentration, 2), round(single_industry_max, 2), industry_count, alerts
    
    async def _get_benchmark_returns(
        self, 
        start_date: date, 
        end_date: date
    ) -> np.ndarray:
        try:
            await self.add_thinking("正在获取沪深300基准数据...")
            benchmark_data = await datasource_manager.get_nav_history(
                "000300",  
                start_date,
                end_date
            )
            
            if benchmark_data and len(benchmark_data) > 1:
                values = np.array([
                    float(d.get("nav", 0)) for d in benchmark_data
                ])
                values = values[values > 0]
                if len(values) > 1:
                    returns = np.diff(values) / values[:-1]
                    await self.add_thinking(f"获取到{len(returns)}条基准收益率数据")
                    return returns
                else:
                    await self.add_thinking("基准数据有效值不足")
            else:
                await self.add_thinking("无法获取基准数据，将跳过Beta计算")
        except Exception as e:
            logger.warning(f"获取沪深300基准数据失败: {e}")
            await self.add_thinking(f"获取基准数据失败: {str(e)}")
        
        return np.array([])
    
    def _estimate_recovery_days(
        self,
        nav_history: List[Dict[str, Any]],
        max_dd_idx: int
    ) -> Optional[int]:
        if not nav_history or max_dd_idx is None or max_dd_idx >= len(nav_history):
            return None
        
        try:
            max_dd_value = float(nav_history[max_dd_idx].get("nav", 0))
            if max_dd_value <= 0:
                return None
            
            peak_value = None
            for i in range(max_dd_idx - 1, -1, -1):
                nav = float(nav_history[i].get("nav", 0))
                if nav > max_dd_value:
                    peak_value = nav
                    break
            
            if peak_value is None:
                return None
            
            for i in range(max_dd_idx + 1, len(nav_history)):
                nav = float(nav_history[i].get("nav", 0))
                if nav >= peak_value:
                    return i - max_dd_idx
            
            return None
        except Exception:
            return None
    
    async def _prepare_risk_metrics(
        self,
        fund_code: str,
        fund_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        await self.add_thinking(f"开始分析基金 {fund_code} 的风险指标...")
        await self.add_thinking(f"分析时间范围: {start_date.isoformat()} 至 {end_date.isoformat()}")
        await self.add_thinking("正在获取净值历史数据...")
        
        try:
            nav_history = await datasource_manager.get_nav_history(
                fund_code, start_date, end_date
            )
            
            if not nav_history or len(nav_history) < 2:
                await self.add_thinking(f"获取到的净值数据不足（当前{len(nav_history) if nav_history else 0}条），无法进行风险分析")
                return {
                    "error": "净值历史数据不足",
                    "data_sufficient": False
                }
            
            await self.add_thinking(f"成功获取到{len(nav_history)}条净值记录，开始计算风险指标...")
            
            quality_report = validate_nav_history(nav_history)
            if quality_report.has_warnings:
                for w in quality_report.warnings:
                    await self.add_thinking(f"数据质量警告: {w['message']}")
            
            nav_values = np.array([
                float(d.get("nav", 0)) for d in nav_history
            ])
            nav_values = nav_values[nav_values > 0]
            
            if len(nav_values) < 2:
                await self.add_thinking("有效净值数据不足（过滤掉0值后）")
                return {
                    "error": "有效净值数据不足",
                    "data_sufficient": False
                }
            
            await self.add_thinking(f"有效净值数据{len(nav_values)}条，计算日收益率...")
            returns = np.diff(nav_values) / nav_values[:-1]
            
            await self.add_thinking("正在计算年化波动率...")
            annual_volatility = calculate_volatility(returns)
            daily_volatility = round(float(np.std(returns, ddof=1) * 100), 4)
            await self.add_thinking(f"近1年年化波动率: {annual_volatility}%，日波动率: {daily_volatility}%")
            
            await self.add_thinking("正在计算最大回撤...")
            max_drawdown, max_dd_idx = calculate_max_drawdown(nav_values)
            
            max_drawdown_date = None
            recovery_days = None
            if max_dd_idx is not None and max_dd_idx < len(nav_history):
                max_drawdown_date = nav_history[max_dd_idx].get("date") or nav_history[max_dd_idx].get("trade_date")
                recovery_days = self._estimate_recovery_days(nav_history, max_dd_idx)
            await self.add_thinking(f"近1年最大回撤: {max_drawdown}%，发生日期: {max_drawdown_date or '未知'}")
            
            current_drawdown = calculate_current_drawdown(nav_values)
            await self.add_thinking(f"当前回撤: {current_drawdown}%")
            
            await self.add_thinking("正在计算夏普比率...")
            sharpe_ratio = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
            sharpe_desc = "优秀" if sharpe_ratio > 1 else ("良好" if sharpe_ratio > 0.5 else "一般")
            await self.add_thinking(f"夏普比率: {sharpe_ratio}（{sharpe_desc}）")
            
            calmar_ratio = calculate_calmar_ratio(returns, max_drawdown)
            sortino_ratio = calculate_sortino_ratio(returns)
            sortino_display = f"{sortino_ratio}" if sortino_ratio is not None else "无下行风险"
            await self.add_thinking(f"卡玛比率: {calmar_ratio}，索提诺比率: {sortino_display}")
            
            await self.add_thinking("正在计算Beta系数...")
            benchmark_returns = await self._get_benchmark_returns(start_date, end_date)
            beta, correlation = calculate_beta(returns, benchmark_returns)
            if beta is not None:
                beta_desc = "略小于市场" if beta < 1 else ("略大于市场" if beta > 1 else "与市场相当")
                await self.add_thinking(f"Beta: {beta}（{beta_desc}），相关系数: {correlation}")
            else:
                await self.add_thinking("基准数据不足，无法计算Beta系数")

            await self.add_thinking("正在计算VaR和CVaR...")
            var_95 = calculate_var(returns, 0.95)
            var_99 = calculate_var(returns, 0.99)
            cvar_95 = calculate_cvar(returns, 0.95)
            if var_95 is not None:
                await self.add_thinking(
                    f"VaR(95%): {var_95 * 100:.2f}%, VaR(99%): {var_99 * 100:.2f}%, "
                    f"CVaR(95%): {cvar_95 * 100:.2f}%"
                )

            await self.add_thinking("正在计算下行风险...")
            downside = calculate_downside_risk(returns)
            if downside is not None:
                await self.add_thinking(f"年化下行风险: {downside}%")

            await self.add_thinking("正在执行压力测试...")
            stress_result = stress_test(nav_values)
            if stress_result.get("data_sufficient", False):
                scenario_names = list(stress_result.get("scenarios", {}).keys())
                await self.add_thinking(f"压力测试完成，模拟场景: {', '.join(scenario_names)}")
            
            volatility_trend = "稳定"
            if len(returns) >= 60:
                recent_vol = np.std(returns[-20:], ddof=1) * np.sqrt(252) * 100
                earlier_vol = np.std(returns[-60:-20], ddof=1) * np.sqrt(252) * 100
                if earlier_vol > 0:
                    change = (recent_vol - earlier_vol) / earlier_vol * 100
                    if change > 20:
                        volatility_trend = "上升"
                    elif change < -20:
                        volatility_trend = "下降"
            
            await self.add_thinking(f"波动率趋势: {volatility_trend}")
            await self.add_thinking("风险指标计算完成")
            
            result = {
                "data_sufficient": True,
                "annual_volatility": annual_volatility,
                "daily_volatility": daily_volatility,
                "volatility_trend": volatility_trend,
                "max_drawdown": max_drawdown,
                "max_drawdown_date": max_drawdown_date,
                "max_drawdown_recovery_days": recovery_days,
                "current_drawdown": current_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "calmar_ratio": calmar_ratio,
                "sortino_ratio": sortino_ratio,
                "sortino_ratio_note": "无下行风险" if sortino_ratio is None else None,
                "beta": beta,
                "correlation": correlation,
                "benchmark": "沪深300",
                "var_95": round(var_95 * 100, 4) if var_95 is not None else None,
                "var_99": round(var_99 * 100, 4) if var_99 is not None else None,
                "cvar_95": round(cvar_95 * 100, 4) if cvar_95 is not None else None,
                "downside_risk": downside,
                "stress_test": stress_result if stress_result.get("data_sufficient") else None,
            }
            annotate_data_source(result, "risk_metrics")
            return result
            
        except Exception as e:
            logger.error(f"计算风险指标异常: {e}", exc_info=True)
            await self.add_thinking(f"风险指标计算过程中发生错误: {str(e)}")
            return {
                "error": str(e),
                "data_sufficient": False
            }
    
    async def _prepare_holdings_data(
        self,
        fund_code: str
    ) -> Dict[str, Any]:
        await self.add_thinking("正在分析持仓集中度风险...")
        
        try:
            holdings = await datasource_manager.get_holdings(fund_code)
            
            quality_report = validate_holdings(holdings)
            if quality_report.has_warnings:
                for w in quality_report.warnings:
                    await self.add_thinking(f"持仓数据质量警告: {w['message']}")
            
            timeliness = check_data_timeliness(holdings.get("report_date") if holdings else None)
            if timeliness and not timeliness.get("is_timely", True):
                await self.add_thinking(f"持仓数据时效性: {timeliness['message']}")
            
            top10_concentration, single_industry_max, industry_count, concentration_alerts = \
                self._calculate_concentration_risk(holdings)
            
            for alert in concentration_alerts:
                await self.add_thinking(alert)
            
            report_date = None
            if holdings:
                report_date = holdings.get("report_date")
            
            return {
                "top10_concentration": top10_concentration,
                "single_industry_max": single_industry_max,
                "industry_count": industry_count,
                "report_date": report_date,
                "concentration_alerts": concentration_alerts
            }
            
        except Exception as e:
            logger.error(f"获取持仓数据异常: {e}", exc_info=True)
            await self.add_thinking(f"持仓数据获取失败: {str(e)}")
            return {
                "error": str(e),
                "top10_concentration": 0.0,
                "single_industry_max": 0.0,
                "industry_count": 0
            }
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        fund_info = context.get("fund_info", {})
        
        risk_metrics = await self._prepare_risk_metrics(fund_code, fund_info)
        
        if not risk_metrics.get("data_sufficient", False):
            self.score = None
            self.data_sufficient = False
            self.confidence = 1
            self.data_sufficiency = "insufficient"
            self.summary = "数据不足，无法评估风险"
            self.details = {
                "risk_level": "未知",
                "error": risk_metrics.get("error", "数据不足")
            }
            return self.to_dict()
        
        holdings_data = await self._prepare_holdings_data(fund_code)
        
        risk_alerts = []
        if holdings_data.get("report_date"):
            risk_alerts.append(f"持仓数据截止{holdings_data['report_date']}，可能存在滞后")
        
        if risk_metrics.get("annual_volatility", 0) > 25:
            risk_alerts.append("年化波动率较高，需关注市场风险")
        
        if risk_metrics.get("max_drawdown", 0) > 20:
            risk_alerts.append("历史最大回撤较大，需关注下行风险")
        
        if not risk_alerts:
            risk_alerts.append("当前风险指标处于正常范围")
        
        risk_metrics["risk_alerts"] = risk_alerts
        
        llm_context = {
            "fund_info": fund_info,
            "risk_metrics": risk_metrics,
            "holdings": holdings_data,
            "additional_info": context.get("additional_info", "")
        }
        
        await self.run_llm_analysis(
            fund_code=fund_code,
            context=llm_context,
            use_rag=True,
            use_tools=True
        )
        
        if self.details and "risk_alerts" not in self.details:
            self.details["risk_alerts"] = risk_alerts
        elif not self.details:
            self.details = {"risk_alerts": risk_alerts}
        
        if self.details and risk_metrics.get("var_95") is not None:
            self.details["var_95"] = risk_metrics["var_95"]
            self.details["var_99"] = risk_metrics["var_99"]
            self.details["cvar_95"] = risk_metrics["cvar_95"]
            self.details["downside_risk"] = risk_metrics["downside_risk"]
        
        if self.details and risk_metrics.get("stress_test"):
            self.details["stress_test"] = risk_metrics["stress_test"]
        
        if not self.summary:
            volatility = risk_metrics.get("annual_volatility", 0)
            max_dd = risk_metrics.get("max_drawdown", 0)
            sharpe = risk_metrics.get("sharpe_ratio", 0)
            risk_level = "高" if volatility > 25 or max_dd > 20 else ("中" if volatility > 15 else "低")
            self.summary = f"风险等级{risk_level}，年化波动率{volatility}%，最大回撤{max_dd}%，夏普比率{sharpe}"
        
        return self.to_dict()
