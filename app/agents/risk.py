"""
风险分析师智能体

负责波动率分析、最大回撤评估、夏普比率计算、风险等级划分
通过LLM驱动进行专业风险评估
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import date, timedelta
import numpy as np
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    """风险分析师智能体"""
    
    def __init__(self):
        super().__init__("risk", "风险分析师")
    
    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """
        计算年化波动率
        
        Args:
            returns: 日收益率数组
            
        Returns:
            年化波动率（百分比）
        """
        if len(returns) < 2:
            return 0.0
        
        std_dev = np.std(returns, ddof=1)
        annual_volatility = std_dev * np.sqrt(252) * 100
        return round(float(annual_volatility), 2)
    
    def _calculate_max_drawdown(self, values: np.ndarray) -> Tuple[float, Optional[int]]:
        """
        计算最大回撤及发生位置
        
        Args:
            values: 净值序列数组
            
        Returns:
            (最大回撤百分比, 最大回撤结束位置索引)
        """
        if len(values) < 2:
            return 0.0, None
        
        cumulative_max = np.maximum.accumulate(values)
        drawdowns = (cumulative_max - values) / cumulative_max * 100
        
        max_drawdown = np.max(drawdowns)
        max_drawdown_idx = np.argmax(drawdowns)
        
        return round(float(max_drawdown), 2), int(max_drawdown_idx)
    
    def _calculate_sharpe_ratio(
        self, 
        returns: np.ndarray, 
        risk_free_rate: float = 0.02
    ) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 日收益率数组
            risk_free_rate: 无风险年化利率（默认2%）
            
        Returns:
            夏普比率
        """
        if len(returns) < 2:
            return 0.0
        
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        mean_excess = np.mean(excess_returns)
        std_returns = np.std(returns, ddof=1)
        
        if std_returns == 0:
            return 0.0
        
        sharpe = mean_excess / std_returns * np.sqrt(252)
        return round(float(sharpe), 2)
    
    def _calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        max_drawdown: float
    ) -> float:
        """
        计算卡玛比率（年化收益率/最大回撤）
        
        Args:
            returns: 日收益率数组
            max_drawdown: 最大回撤百分比
            
        Returns:
            卡玛比率
        """
        if len(returns) < 2 or max_drawdown <= 0:
            return 0.0
        
        annual_return = np.mean(returns) * 252 * 100
        calmar = annual_return / max_drawdown
        return round(float(calmar), 2)
    
    def _calculate_sortino_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """
        计算索提诺比率（只考虑下行风险）
        
        Args:
            returns: 日收益率数组
            risk_free_rate: 无风险年化利率
            
        Returns:
            索提诺比率
        """
        if len(returns) < 2:
            return 0.0
        
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        negative_returns = returns[returns < daily_rf]
        if len(negative_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_std = np.std(negative_returns, ddof=1)
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(252)
        return round(float(sortino), 2)
    
    def _calculate_beta(
        self, 
        fund_returns: np.ndarray, 
        benchmark_returns: np.ndarray
    ) -> Tuple[float, float]:
        """
        计算 Beta 系数和相关系数
        
        Args:
            fund_returns: 基金日收益率数组
            benchmark_returns: 基准日收益率数组
            
        Returns:
            (Beta 系数, 相关系数)
        """
        if len(fund_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0, 0.0
        
        min_len = min(len(fund_returns), len(benchmark_returns))
        fund_returns = fund_returns[:min_len]
        benchmark_returns = benchmark_returns[:min_len]
        
        covariance = np.cov(fund_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)
        
        if benchmark_variance == 0:
            return 1.0, 0.0
        
        beta = covariance / benchmark_variance
        
        fund_std = np.std(fund_returns, ddof=1)
        benchmark_std = np.std(benchmark_returns, ddof=1)
        if fund_std == 0 or benchmark_std == 0:
            correlation = 0.0
        else:
            correlation = covariance / (fund_std * benchmark_std)
        
        return round(float(beta), 2), round(float(correlation), 2)
    
    def _calculate_concentration_risk(
        self, 
        holdings: Optional[Dict[str, Any]]
    ) -> Tuple[float, float, int, List[str]]:
        """
        计算集中度风险
        
        Args:
            holdings: 持仓数据
            
        Returns:
            (前十大持仓占比, 单一行业最大占比, 行业数量, 风险提示列表)
        """
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
        """
        获取基准（沪深300）收益率数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            基准日收益率数组
        """
        try:
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
                    return returns
        except Exception as e:
            logger.warning(f"获取沪深300基准数据失败: {e}")
        
        return np.array([])
    
    def _calculate_current_drawdown(self, values: np.ndarray) -> float:
        """
        计算当前回撤
        
        Args:
            values: 净值序列数组
            
        Returns:
            当前回撤百分比
        """
        if len(values) < 2:
            return 0.0
        
        cumulative_max = np.maximum.accumulate(values)
        current_value = values[-1]
        current_max = cumulative_max[-1]
        
        if current_max == 0:
            return 0.0
        
        current_drawdown = (current_max - current_value) / current_max * 100
        return round(float(current_drawdown), 2)
    
    def _estimate_recovery_days(
        self,
        nav_history: List[Dict[str, Any]],
        max_dd_idx: int
    ) -> Optional[int]:
        """
        估算最大回撤恢复天数
        
        Args:
            nav_history: 净值历史数据
            max_dd_idx: 最大回撤位置索引
            
        Returns:
            恢复天数（如果已恢复）或 None
        """
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
        """
        准备风险指标数据
        
        Args:
            fund_code: 基金代码
            fund_info: 基金基础信息
            
        Returns:
            风险指标字典
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        await self.add_thinking("正在获取净值历史数据...")
        
        try:
            nav_history = await datasource_manager.get_nav_history(
                fund_code, start_date, end_date
            )
            
            if not nav_history or len(nav_history) < 2:
                await self.add_thinking("净值数据不足，无法进行风险分析")
                return {
                    "error": "净值历史数据不足",
                    "data_sufficient": False
                }
            
            await self.add_thinking(f"获取到{len(nav_history)}条净值记录，开始计算风险指标...")
            
            nav_values = np.array([
                float(d.get("nav", 0)) for d in nav_history
            ])
            nav_values = nav_values[nav_values > 0]
            
            if len(nav_values) < 2:
                await self.add_thinking("有效净值数据不足")
                return {
                    "error": "有效净值数据不足",
                    "data_sufficient": False
                }
            
            returns = np.diff(nav_values) / nav_values[:-1]
            
            await self.add_thinking("正在计算年化波动率...")
            annual_volatility = self._calculate_volatility(returns)
            daily_volatility = round(float(np.std(returns, ddof=1) * 100), 4)
            await self.add_thinking(f"近1年年化波动率{annual_volatility}%...")
            
            await self.add_thinking("正在计算最大回撤...")
            max_drawdown, max_dd_idx = self._calculate_max_drawdown(nav_values)
            
            max_drawdown_date = None
            recovery_days = None
            if max_dd_idx is not None and max_dd_idx < len(nav_history):
                max_drawdown_date = nav_history[max_dd_idx].get("date")
                recovery_days = self._estimate_recovery_days(nav_history, max_dd_idx)
            await self.add_thinking(f"近1年最大回撤{max_drawdown}%，发生在{max_drawdown_date or '未知'}...")
            
            current_drawdown = self._calculate_current_drawdown(nav_values)
            
            await self.add_thinking("正在计算夏普比率...")
            sharpe_ratio = self._calculate_sharpe_ratio(returns, risk_free_rate=0.02)
            sharpe_desc = "优秀" if sharpe_ratio > 1 else ("良好" if sharpe_ratio > 0.5 else "一般")
            await self.add_thinking(f"夏普比率{sharpe_ratio}，评价{sharpe_desc}...")
            
            calmar_ratio = self._calculate_calmar_ratio(returns, max_drawdown)
            sortino_ratio = self._calculate_sortino_ratio(returns)
            
            await self.add_thinking("正在计算Beta系数...")
            benchmark_returns = await self._get_benchmark_returns(start_date, end_date)
            beta, correlation = self._calculate_beta(returns, benchmark_returns)
            beta_desc = "略小于市场" if beta < 1 else ("略大于市场" if beta > 1 else "与市场相当")
            await self.add_thinking(f"Beta={beta}，波动{beta_desc}...")
            
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
            
            return {
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
                "beta": beta,
                "correlation": correlation,
                "benchmark": "沪深300"
            }
            
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
        """
        准备持仓集中度数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            持仓数据字典
        """
        await self.add_thinking("正在分析持仓集中度风险...")
        
        try:
            holdings = await datasource_manager.get_holdings(fund_code)
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
        """
        执行风险分析
        
        通过LLM驱动进行专业风险评估，
        风险指标计算结果作为上下文数据提供给LLM
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            
        Returns:
            分析结果字典
        """
        fund_info = context.get("fund_info", {})
        
        risk_metrics = await self._prepare_risk_metrics(fund_code, fund_info)
        
        if not risk_metrics.get("data_sufficient", False):
            self.score = 0.0
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
        
        # 确保 risk_alerts 存入 self.details，供报告生成使用
        if self.details and "risk_alerts" not in self.details:
            self.details["risk_alerts"] = risk_alerts
        elif not self.details:
            self.details = {"risk_alerts": risk_alerts}
        
        # 兜底逻辑：若 LLM 未返回 summary，根据风险指标生成默认摘要
        if not self.summary:
            volatility = risk_metrics.get("annual_volatility", 0)
            max_dd = risk_metrics.get("max_drawdown", 0)
            sharpe = risk_metrics.get("sharpe_ratio", 0)
            risk_level = "高" if volatility > 25 or max_dd > 20 else ("中" if volatility > 15 else "低")
            self.summary = f"风险等级{risk_level}，年化波动率{volatility}%，最大回撤{max_dd}%，夏普比率{sharpe}"
        
        return self.to_dict()
