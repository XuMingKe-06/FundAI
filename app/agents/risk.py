"""
风险分析师智能体
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
    
    def _calculate_beta(
        self, 
        fund_returns: np.ndarray, 
        benchmark_returns: np.ndarray
    ) -> float:
        """
        计算 Beta 系数
        
        Args:
            fund_returns: 基金日收益率数组
            benchmark_returns: 基准日收益率数组
            
        Returns:
            Beta 系数
        """
        if len(fund_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0
        
        min_len = min(len(fund_returns), len(benchmark_returns))
        fund_returns = fund_returns[:min_len]
        benchmark_returns = benchmark_returns[:min_len]
        
        covariance = np.cov(fund_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)
        
        if benchmark_variance == 0:
            return 1.0
        
        beta = covariance / benchmark_variance
        return round(float(beta), 2)
    
    def _assess_risk_level(self, volatility: float, max_drawdown: float) -> str:
        """
        评估风险等级
        
        Args:
            volatility: 年化波动率
            max_drawdown: 最大回撤
            
        Returns:
            风险等级（低/中/高）
        """
        risk_score = 0
        
        if volatility < 10:
            risk_score += 1
        elif volatility < 20:
            risk_score += 2
        else:
            risk_score += 3
        
        if max_drawdown < 10:
            risk_score += 1
        elif max_drawdown < 20:
            risk_score += 2
        else:
            risk_score += 3
        
        if risk_score <= 3:
            return "低"
        elif risk_score <= 5:
            return "中"
        else:
            return "高"
    
    def _calculate_concentration_risk(
        self, 
        holdings: Optional[Dict[str, Any]]
    ) -> Tuple[float, float, List[str]]:
        """
        计算集中度风险
        
        Args:
            holdings: 持仓数据
            
        Returns:
            (前十大持仓占比, 单一行业最大占比, 风险提示列表)
        """
        alerts = []
        top10_concentration = 0.0
        single_industry_max = 0.0
        
        if not holdings:
            alerts.append("无法获取持仓数据，集中度风险未知")
            return top10_concentration, single_industry_max, alerts
        
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
        
        return round(top10_concentration, 2), round(single_industry_max, 2), alerts
    
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
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行风险分析"""
        fund_info = context.get("fund_info", {})
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        self.add_thinking("正在获取净值历史数据...")
        
        try:
            nav_history = await datasource_manager.get_nav_history(
                fund_code, start_date, end_date
            )
            
            if not nav_history or len(nav_history) < 2:
                self.add_thinking("净值数据不足，无法进行风险分析")
                self.score = 0.0
                self.summary = "数据不足，无法评估风险"
                self.details = {
                    "risk_level": "未知",
                    "error": "净值历史数据不足"
                }
                return self.to_dict()
            
            self.add_thinking(f"获取到{len(nav_history)}条净值记录，开始计算风险指标...")
            
            nav_values = np.array([
                float(d.get("nav", 0)) for d in nav_history
            ])
            nav_values = nav_values[nav_values > 0]
            
            if len(nav_values) < 2:
                self.add_thinking("有效净值数据不足")
                self.score = 0.0
                self.summary = "数据不足，无法评估风险"
                self.details = {
                    "risk_level": "未知",
                    "error": "有效净值数据不足"
                }
                return self.to_dict()
            
            returns = np.diff(nav_values) / nav_values[:-1]
            
            self.add_thinking("正在计算年化波动率...")
            annual_volatility = self._calculate_volatility(returns)
            self.add_thinking(f"近1年年化波动率{annual_volatility}%...")
            
            self.add_thinking("正在计算最大回撤...")
            max_drawdown, max_dd_idx = self._calculate_max_drawdown(nav_values)
            
            max_drawdown_date = None
            if max_dd_idx is not None and max_dd_idx < len(nav_history):
                max_drawdown_date = nav_history[max_dd_idx].get("date")
            self.add_thinking(f"近1年最大回撤{max_drawdown}%，发生在{max_drawdown_date or '未知'}...")
            
            self.add_thinking("正在计算夏普比率...")
            sharpe_ratio = self._calculate_sharpe_ratio(returns, risk_free_rate=0.02)
            sharpe_desc = "优秀" if sharpe_ratio > 1 else ("良好" if sharpe_ratio > 0.5 else "一般")
            self.add_thinking(f"夏普比率{sharpe_ratio}，评价{sharpe_desc}...")
            
            self.add_thinking("正在计算Beta系数...")
            benchmark_returns = await self._get_benchmark_returns(start_date, end_date)
            beta = self._calculate_beta(returns, benchmark_returns)
            beta_desc = "略小于市场" if beta < 1 else ("略大于市场" if beta > 1 else "与市场相当")
            self.add_thinking(f"Beta={beta}，波动{beta_desc}...")
            
            self.add_thinking("正在分析持仓集中度风险...")
            holdings = await datasource_manager.get_holdings(fund_code)
            top10_concentration, single_industry_max, concentration_alerts = \
                self._calculate_concentration_risk(holdings)
            
            for alert in concentration_alerts:
                self.add_thinking(alert)
            
            risk_level = self._assess_risk_level(annual_volatility, max_drawdown)
            
            risk_alerts = []
            if holdings:
                report_date = holdings.get("report_date")
                if report_date:
                    risk_alerts.append(f"持仓数据截止{report_date}，可能存在滞后")
            
            if annual_volatility > 25:
                risk_alerts.append("年化波动率较高，需关注市场风险")
            
            if max_drawdown > 20:
                risk_alerts.append("历史最大回撤较大，需关注下行风险")
            
            if not risk_alerts:
                risk_alerts.append("当前风险指标处于正常范围")
            
            if risk_level == "低":
                self.score = 4.5
            elif risk_level == "中":
                self.score = 3.5
            else:
                self.score = 2.0
            
            if risk_level == "高":
                self.summary = "波动率较高，需谨慎投资"
            elif risk_level == "中":
                self.summary = "波动率适中，需关注集中度风险"
            else:
                self.summary = "风险水平较低，适合稳健投资"
            
            self.details = {
                "risk_level": risk_level,
                "annual_volatility": annual_volatility,
                "max_drawdown": max_drawdown,
                "max_drawdown_date": max_drawdown_date,
                "sharpe_ratio": sharpe_ratio,
                "beta": beta,
                "top10_concentration": top10_concentration,
                "single_industry_max": single_industry_max,
                "risk_alerts": risk_alerts
            }
            
            self.add_thinking(f"综合评估：风险等级{risk_level}。{self.summary}。")
            
        except Exception as e:
            logger.error(f"风险分析异常: {e}", exc_info=True)
            self.add_thinking(f"风险分析过程中发生错误: {str(e)}")
            self.score = 0.0
            self.summary = "风险分析失败"
            self.details = {
                "risk_level": "未知",
                "error": str(e)
            }
        
        return self.to_dict()
