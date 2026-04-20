"""
基本面分析师智能体
"""
from typing import Dict, Any
from datetime import datetime, date, timedelta
import asyncio

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager


class FundamentalAgent(BaseAgent):
    """基本面分析师智能体"""
    
    def __init__(self):
        super().__init__("fundamental", "基本面分析师")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行基本面分析"""
        # 初始化评分因子
        score_factors = []
        
        # 1. 获取基金基础信息
        self.add_thinking("正在获取基金基础信息...")
        fund_info = await self._get_fund_info(fund_code)
        
        fund_name = fund_info.get("fund_name", "未知") if fund_info else "未知"
        fund_scale = fund_info.get("current_scale", 0) if fund_info else 0
        fund_manager_name = fund_info.get("fund_manager", "未知") if fund_info else "未知"
        
        self.add_thinking(f"获取到基金概况：{fund_name}，当前规模{fund_scale}亿，基金经理{fund_manager_name}...")
        
        # 2. 获取持仓结构数据
        self.add_thinking("正在分析持仓结构...")
        holdings_data = await self._get_holdings(fund_code)
        holding_analysis = self._analyze_holdings(holdings_data)
        
        top10_ratio = holding_analysis.get("top10_holding_ratio", 0)
        industry_concentration = holding_analysis.get("industry_concentration", "未知")
        holding_date = holding_analysis.get("report_date", "未知")
        
        self.add_thinking(f"前十大重仓股占比{top10_ratio:.1f}%，行业分布{industry_concentration}，集中度评价：{self._get_concentration_level(top10_ratio)}...")
        
        # 根据持仓集中度评分
        holding_score = self._calculate_holding_score(top10_ratio)
        score_factors.append(("持仓结构", holding_score))
        
        # RAG检索：检索相似持仓结构案例
        try:
            holding_knowledge = await self.retrieve_knowledge(
                query=f"基金持仓 {industry_concentration} 行业配置 分析",
                collection_name="analysis_cases",
                top_k=3
            )
            if holding_knowledge:
                self._rag_context.extend([
                    item.get("content", "") for item in holding_knowledge if item.get("content")
                ])
        except Exception as e:
            self.add_thinking(f"持仓结构案例检索失败: {str(e)}")
        
        # 3. 获取基金经理信息
        self.add_thinking("正在分析基金经理履历...")
        manager_info = await self._get_fund_manager(fund_code)
        manager_analysis = self._analyze_manager(manager_info)
        
        experience_years = manager_analysis.get("experience_years", 0)
        manager_score = manager_analysis.get("score", 2.5)
        
        self.add_thinking(f"基金经理从业经验{experience_years}年，管理本基金时间{'较长' if experience_years >= 5 else '一般'}，任期回报{'优秀' if manager_score >= 4 else '良好'}...")
        
        # RAG检索：检索基金经理历史表现报告
        try:
            manager_knowledge = await self.retrieve_knowledge(
                query=f"基金经理 {fund_manager_name} 历史表现 管理能力",
                collection_name="fund_knowledge",
                top_k=3
            )
            if manager_knowledge:
                self._rag_context.extend([
                    item.get("content", "") for item in manager_knowledge if item.get("content")
                ])
        except Exception as e:
            self.add_thinking(f"基金经理知识检索失败: {str(e)}")
        
        score_factors.append(("基金经理", manager_score))
        
        # 4. 计算业绩基准比较
        self.add_thinking("正在计算业绩基准比较...")
        performance_data = await self._get_performance_data(fund_code)
        performance_analysis = self._analyze_performance(performance_data)
        
        alpha_1y = performance_analysis.get("alpha_1y", 0)
        information_ratio = performance_analysis.get("information_ratio", 0)
        performance_score = performance_analysis.get("score", 2.5)
        
        self.add_thinking(f"近1年超额收益率{alpha_1y:.2f}%，信息比率{information_ratio:.2f}，表现{self._get_performance_level(performance_score)}...")
        
        score_factors.append(("业绩表现", performance_score))
        
        # 5. 计算综合评分
        self.score = self._calculate_weighted_score(score_factors)
        
        # 生成摘要
        self.summary = self._generate_summary(
            fund_manager_name, 
            experience_years, 
            industry_concentration, 
            performance_score
        )
        
        # 构建详细信息
        self.details = {
            "fund_manager": fund_manager_name,
            "management_experience_years": experience_years,
            "fund_scale": float(fund_scale) if fund_scale else 0,
            "top10_holding_ratio": round(top10_ratio, 2),
            "industry_concentration": industry_concentration,
            "alpha_1y": round(alpha_1y, 2),
            "information_ratio": round(information_ratio, 2),
            "holding_data_date": holding_date,
            "score_factors": {name: round(score, 2) for name, score in score_factors}
        }
        
        self.add_thinking(f"综合评估：基本面评分{self.score:.1f}分。{self.summary}。")
        
        return self.to_dict()
    
    async def _get_fund_info(self, fund_code: str) -> Dict[str, Any]:
        """获取基金基础信息"""
        try:
            result = await datasource_manager.get_fund_info(fund_code)
            return result or {}
        except Exception as e:
            self.add_thinking(f"获取基金基础信息失败: {str(e)}")
            return {}
    
    async def _get_holdings(self, fund_code: str) -> Dict[str, Any]:
        """获取持仓信息"""
        try:
            result = await datasource_manager.get_holdings(fund_code)
            return result or {}
        except Exception as e:
            self.add_thinking(f"获取持仓信息失败: {str(e)}")
            return {}
    
    async def _get_fund_manager(self, fund_code: str) -> Dict[str, Any]:
        """获取基金经理信息"""
        try:
            result = await datasource_manager.get_fund_manager(fund_code)
            return result or {}
        except Exception as e:
            self.add_thinking(f"获取基金经理信息失败: {str(e)}")
            return {}
    
    async def _get_performance_data(self, fund_code: str) -> Dict[str, Any]:
        """获取业绩数据（通过净值历史计算）"""
        try:
            # 获取近一年的净值历史数据
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            
            nav_history = await datasource_manager.get_nav_history(
                fund_code, start_date, end_date
            )
            return {"nav_history": nav_history} if nav_history else {}
        except Exception as e:
            self.add_thinking(f"获取业绩数据失败: {str(e)}")
            return {}
    
    def _analyze_holdings(self, holdings_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析持仓结构"""
        if not holdings_data:
            return {
                "top10_holding_ratio": 0,
                "industry_concentration": "未知",
                "report_date": "未知"
            }
        
        # 获取前十大持仓占比
        stock_list = holdings_data.get("stock_list", [])
        if stock_list and len(stock_list) > 0:
            # 计算前十大持仓占比
            top10_ratio = sum(
                float(holding.get("holding_ratio", 0)) 
                for holding in stock_list[:10]
            )
            
            # 分析行业分布
            industries = {}
            for holding in stock_list:
                industry = holding.get("industry", "未知")
                ratio = float(holding.get("holding_ratio", 0))
                industries[industry] = industries.get(industry, 0) + ratio
            
            # 获取前三大行业
            sorted_industries = sorted(
                industries.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            industry_concentration = "、".join([ind[0] for ind in sorted_industries]) if sorted_industries else "未知"
            
            report_date = holdings_data.get("report_date", "未知")
        else:
            top10_ratio = 0
            industry_concentration = "未知"
            report_date = "未知"
        
        return {
            "top10_holding_ratio": top10_ratio,
            "industry_concentration": industry_concentration,
            "report_date": report_date
        }
    
    def _analyze_manager(self, manager_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析基金经理信息"""
        if not manager_info:
            return {"experience_years": 0, "score": 2.5}
        
        # 获取从业经验
        experience_years = manager_info.get("experience_years", 0)
        if experience_years == 0:
            # 尝试从任职日期计算
            start_date = manager_info.get("start_date")
            if start_date:
                try:
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    experience_years = (date.today() - start_date).days / 365
                except Exception:
                    experience_years = 0
        
        # 根据从业经验评分
        if experience_years >= 10:
            score = 5.0
        elif experience_years >= 7:
            score = 4.0
        elif experience_years >= 5:
            score = 3.5
        elif experience_years >= 3:
            score = 3.0
        else:
            score = 2.5
        
        # 考虑历史业绩（如有）
        annual_return = manager_info.get("annual_return")
        if annual_return is not None:
            try:
                annual_return = float(annual_return)
                if annual_return > 15:
                    score = min(5.0, score + 0.5)
                elif annual_return > 10:
                    score = min(5.0, score + 0.3)
            except Exception:
                pass
        
        return {
            "experience_years": round(experience_years, 1),
            "score": score
        }
    
    def _analyze_performance(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析业绩表现"""
        nav_history = performance_data.get("nav_history", [])
        
        if not nav_history or len(nav_history) < 2:
            return {
                "alpha_1y": 0,
                "information_ratio": 0,
                "score": 2.5
            }
        
        try:
            # 计算收益率
            first_nav = float(nav_history[0].get("nav", 0))
            last_nav = float(nav_history[-1].get("nav", 0))
            
            if first_nav > 0:
                total_return = (last_nav - first_nav) / first_nav * 100
            else:
                total_return = 0
            
            # 假设基准收益率为8%（可从配置获取）
            benchmark_return = 8.0
            alpha_1y = total_return - benchmark_return
            
            # 简化计算信息比率（实际应使用跟踪误差）
            # 这里使用收益率与基准的比率作为近似
            if benchmark_return > 0:
                information_ratio = total_return / benchmark_return - 1
            else:
                information_ratio = 0
            
            # 根据超额收益评分
            if alpha_1y >= 10:
                score = 5.0
            elif alpha_1y >= 5:
                score = 4.0
            elif alpha_1y >= 0:
                score = 3.0
            elif alpha_1y >= -5:
                score = 2.0
            else:
                score = 1.0
            
            return {
                "alpha_1y": alpha_1y,
                "information_ratio": information_ratio,
                "score": score
            }
        except Exception:
            return {
                "alpha_1y": 0,
                "information_ratio": 0,
                "score": 2.5
            }
    
    def _calculate_holding_score(self, top10_ratio: float) -> float:
        """根据持仓集中度计算评分"""
        # 持仓集中度适中为最佳（30%-50%）
        if 30 <= top10_ratio <= 50:
            return 4.5
        elif 20 <= top10_ratio < 30 or 50 < top10_ratio <= 60:
            return 4.0
        elif 10 <= top10_ratio < 20 or 60 < top10_ratio <= 70:
            return 3.5
        else:
            return 3.0
    
    def _calculate_weighted_score(self, score_factors: list) -> float:
        """计算加权评分"""
        # 权重配置：基金经理30%，持仓结构25%，业绩表现45%
        weights = {
            "基金经理": 0.30,
            "持仓结构": 0.25,
            "业绩表现": 0.45
        }
        
        total_score = 0
        total_weight = 0
        
        for factor_name, score in score_factors:
            weight = weights.get(factor_name, 0.25)
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 2.5
        
        # 确保评分在1-5范围内
        return max(1.0, min(5.0, round(final_score, 1)))
    
    def _get_concentration_level(self, ratio: float) -> str:
        """获取集中度评价等级"""
        if ratio < 20:
            return "较低"
        elif ratio < 40:
            return "中等偏低"
        elif ratio < 60:
            return "中等"
        elif ratio < 70:
            return "较高"
        else:
            return "很高"
    
    def _get_performance_level(self, score: float) -> str:
        """获取业绩表现等级描述"""
        if score >= 4.5:
            return "优秀"
        elif score >= 3.5:
            return "良好"
        elif score >= 2.5:
            return "一般"
        else:
            return "较差"
    
    def _generate_summary(
        self, 
        manager_name: str, 
        experience_years: float, 
        industry_concentration: str, 
        performance_score: float
    ) -> str:
        """生成分析摘要"""
        parts = []
        
        # 基金经理评价
        if experience_years >= 7:
            parts.append("基金经理经验丰富")
        elif experience_years >= 3:
            parts.append("基金经理经验适中")
        else:
            parts.append("基金经理经验较少")
        
        # 持仓结构评价
        if industry_concentration and industry_concentration != "未知":
            parts.append(f"持仓以{industry_concentration}为主")
        
        # 业绩表现评价
        if performance_score >= 4:
            parts.append("业绩表现优秀")
        elif performance_score >= 3:
            parts.append("业绩表现良好")
        else:
            parts.append("业绩表现一般")
        
        return "，".join(parts)
