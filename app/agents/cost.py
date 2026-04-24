"""
成本分析师智能体

负责基金费率结构分析、成本矩阵计算、短线可行性评估
采用LLM驱动的分析方法，通过提示词模板引导分析过程
"""
from typing import Dict, Any, List
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager


logger = logging.getLogger(__name__)


class CostAgent(BaseAgent):
    """成本分析师智能体"""
    
    DEFAULT_REDEMPTION_LADDER = [
        {"min_days": 0, "max_days": 7, "fee_rate": 0.015, "description": "不满7天"},
        {"min_days": 7, "max_days": 30, "fee_rate": 0.0075, "description": "7-30天"},
        {"min_days": 30, "max_days": 365, "fee_rate": 0.005, "description": "30天-1年"},
        {"min_days": 365, "max_days": 730, "fee_rate": 0.0025, "description": "1-2年"},
        {"min_days": 730, "max_days": None, "fee_rate": 0.0, "description": "2年以上"},
    ]
    
    HOLDING_PERIODS = [
        {"days": 7, "label": "7天"},
        {"days": 15, "label": "15天"},
        {"days": 30, "label": "30天"},
        {"days": 180, "label": "180天"},
        {"days": 365, "label": "1年"},
    ]
    
    DEFAULT_EXPECTED_RETURN = 0.042
    
    def __init__(self):
        super().__init__("cost", "成本分析师")
        self._computed_cost_matrix: List[Dict[str, Any]] = []
        self._computed_fees: Dict[str, Any] = {}
        self._computed_feasibility: Dict[str, Any] = {}
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行成本分析
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，可包含：
                - fund_info: 基金基础信息
                - expected_return: 预期毛收益率（可选）
                
        Returns:
            分析结果字典
        """
        try:
            enhanced_context = await self._prepare_analysis_context(fund_code, context)
            
            # 保存代码计算的精确数据，用于 LLM 输出缺失时兜底
            self._computed_cost_matrix = enhanced_context.get("cost_matrix", [])
            self._computed_fees = enhanced_context.get("fees", {})
            self._computed_feasibility = enhanced_context.get("feasibility_analysis", {})
            
            result = await self.run_llm_analysis(
                fund_code=fund_code,
                context=enhanced_context,
                use_rag=True,
                use_tools=True
            )
            
            # 用代码计算的精确数据补充/覆盖 LLM 可能缺失的字段
            self._ensure_computed_data()
            
            return self.to_dict()
            
        except Exception as e:
            logger.error(f"成本分析失败: {e}", exc_info=True)
            await self.add_thinking(f"成本分析过程中发生错误: {str(e)}")
            self.score = 0.0
            self.summary = "成本分析失败"
            self.details = {
                "error": str(e),
                "purchase_fee_rate": None,
                "redemption_fee_ladder": [],
                "cost_matrix": [],
                "short_term_feasibility": "无法评估",
                "recommended_holding_period": None,
            }
            return self.to_dict()
    
    def _ensure_computed_data(self) -> None:
        """用代码计算的精确数据补充/覆盖 LLM 输出中可能缺失的字段"""
        if self.details is None:
            self.details = {}
        
        # 确保成本矩阵使用代码计算的精确值
        if not self.details.get("cost_matrix"):
            self.details["cost_matrix"] = self._computed_cost_matrix
        
        # 确保赎回费率阶梯使用代码计算的精确值
        if not self.details.get("redemption_fee_ladder"):
            self.details["redemption_fee_ladder"] = self._computed_fees.get("redemption_ladder", [])
        
        # 确保申购费率使用代码计算的精确值
        if self.details.get("purchase_fee_rate") is None:
            self.details["purchase_fee_rate"] = self._computed_fees.get("purchase_fee_discounted")
        
        # 确保 summary 不为空
        if not self.summary:
            feasibility = self._computed_feasibility
            profitable = feasibility.get("profitable_count", 0)
            total = feasibility.get("total_count", 0)
            if profitable == total and total > 0:
                self.summary = f"短线投资具备成本可行性，{profitable}/{total}个方案盈利"
            elif profitable > 0:
                self.summary = f"短线投资部分具备成本可行性，{profitable}/{total}个方案盈利"
            elif total > 0:
                self.summary = f"短线投资不具备成本可行性，{profitable}/{total}个方案盈利"
            else:
                self.summary = "成本分析完成，数据不足无法评估短线可行性"
    
    async def _prepare_analysis_context(
        self,
        fund_code: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        准备分析上下文数据
        
        获取费率信息并构建成本矩阵，作为LLM分析的输入数据
        
        Args:
            fund_code: 基金代码
            context: 原始上下文
            
        Returns:
            增强后的上下文
        """
        fund_info = context.get("fund_info", {})
        expected_return = context.get("expected_return", self.DEFAULT_EXPECTED_RETURN)
        
        await self.add_thinking("正在获取基金费率信息...")
        fees_data = await datasource_manager.get_fund_fees(fund_code)
        
        fees_info = {}
        if fees_data is None:
            await self.add_thinking("无法从数据源获取费率信息，将使用默认费率进行估算")
            purchase_fee = 0.0015
            redemption_ladder = self.DEFAULT_REDEMPTION_LADDER
            fees_info = {
                "purchase_fee_original": 0.015,
                "purchase_fee_discounted": purchase_fee,
                "management_fee": None,
                "custody_fee": None,
                "sales_service_fee": None,
                "redemption_ladder": redemption_ladder,
            }
        else:
            purchase_fee = self._parse_purchase_fee(fees_data)
            redemption_ladder = self._parse_redemption_ladder(fees_data)
            
            fees_info = {
                "purchase_fee_original": fees_data.get("purchase_fee"),
                "purchase_fee_discounted": purchase_fee,
                "management_fee": fees_data.get("management_fee"),
                "custody_fee": fees_data.get("custody_fee"),
                "sales_service_fee": fees_data.get("sales_service_fee"),
                "redemption_ladder": redemption_ladder,
            }
            
            await self.add_thinking(
                f"申购费率原价{self._format_rate(fees_data.get('purchase_fee'))}，"
                f"代销平台折扣后{self._format_rate(purchase_fee)}"
            )
        
        await self.add_thinking("正在构建成本矩阵...")
        cost_matrix = self._build_cost_matrix(purchase_fee, redemption_ladder)
        
        feasibility_analysis = self._prepare_feasibility_data(cost_matrix, expected_return)
        
        enhanced_context = {
            **context,
            "fund_info": fund_info,
            "fees": fees_info,
            "cost_matrix": cost_matrix,
            "expected_return": expected_return,
            "feasibility_analysis": feasibility_analysis,
        }
        
        await self.add_thinking(f"成本矩阵构建完成，共{len(cost_matrix)}个持有期方案")
        
        return enhanced_context
    
    def _parse_purchase_fee(self, fees_data: Dict[str, Any]) -> float:
        """
        解析申购费率
        
        Args:
            fees_data: 费率数据
            
        Returns:
            申购费率（考虑平台折扣）
        """
        original_fee = fees_data.get("purchase_fee")
        if original_fee is not None:
            return float(original_fee) * 0.1
        return 0.0015
    
    def _parse_redemption_ladder(self, fees_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析赎回费率阶梯
        
        Args:
            fees_data: 费率数据
            
        Returns:
            赎回费率阶梯列表
        """
        base_redemption_fee = fees_data.get("redemption_fee")
        
        if base_redemption_fee is not None:
            ladder = []
            for item in self.DEFAULT_REDEMPTION_LADDER:
                adjusted_item = item.copy()
                if item["fee_rate"] > 0:
                    ratio = float(base_redemption_fee) / 0.005
                    adjusted_item["fee_rate"] = round(item["fee_rate"] * ratio, 4)
                ladder.append(adjusted_item)
            return ladder
        
        return self.DEFAULT_REDEMPTION_LADDER
    
    def _build_cost_matrix(
        self,
        purchase_fee: float,
        redemption_ladder: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        构建成本矩阵
        
        Args:
            purchase_fee: 申购费率
            redemption_ladder: 赎回费率阶梯
            
        Returns:
            成本矩阵列表
        """
        cost_matrix = []
        
        for period in self.HOLDING_PERIODS:
            days = period["days"]
            label = period["label"]
            
            redemption_fee = self._get_redemption_fee(days, redemption_ladder)
            total_fee = purchase_fee + redemption_fee
            breakeven = self._calculate_breakeven(total_fee)
            
            cost_matrix.append({
                "holding_period": label,
                "holding_days": days,
                "purchase_fee": round(purchase_fee, 4),
                "redemption_fee": round(redemption_fee, 4),
                "total_fee": round(total_fee, 4),
                "breakeven": round(breakeven, 4),
            })
        
        return cost_matrix
    
    def _get_redemption_fee(
        self,
        holding_days: int,
        redemption_ladder: List[Dict[str, Any]]
    ) -> float:
        """
        根据持有天数获取赎回费率
        
        Args:
            holding_days: 持有天数
            redemption_ladder: 赎回费率阶梯
            
        Returns:
            对应的赎回费率
        """
        for item in redemption_ladder:
            min_days = item["min_days"]
            max_days = item["max_days"]
            
            if max_days is None:
                if holding_days >= min_days:
                    return item["fee_rate"]
            else:
                if min_days <= holding_days < max_days:
                    return item["fee_rate"]
        
        return redemption_ladder[-1]["fee_rate"]
    
    def _calculate_breakeven(self, total_fee: float) -> float:
        """
        计算盈亏平衡点
        
        Args:
            total_fee: 总费率
            
        Returns:
            盈亏平衡点
        """
        if total_fee >= 1:
            return float('inf')
        
        return total_fee / (1 - total_fee)
    
    def _prepare_feasibility_data(
        self,
        cost_matrix: List[Dict[str, Any]],
        expected_return: float
    ) -> Dict[str, Any]:
        """
        准备可行性分析数据供LLM参考
        
        Args:
            cost_matrix: 成本矩阵
            expected_return: 预期毛收益率
            
        Returns:
            可行性分析数据
        """
        short_term_periods = [item for item in cost_matrix if item["holding_days"] <= 30]
        
        if not short_term_periods:
            return {
                "feasibility": "无法评估",
                "analysis_text": "缺少短线持有期数据",
                "net_returns": [],
            }
        
        net_returns = []
        for item in short_term_periods:
            net_return = expected_return - item["total_fee"]
            net_returns.append({
                "holding_period": item["holding_period"],
                "holding_days": item["holding_days"],
                "expected_return": round(expected_return, 4),
                "total_fee": item["total_fee"],
                "net_return": round(net_return, 4),
                "is_profitable": net_return > 0,
            })
        
        profitable_options = [nr for nr in net_returns if nr["is_profitable"]]
        
        return {
            "net_returns": net_returns,
            "profitable_count": len(profitable_options),
            "total_count": len(net_returns),
        }
    
    def _format_rate(self, rate: float) -> str:
        """
        格式化费率显示
        
        Args:
            rate: 费率值
            
        Returns:
            格式化后的费率字符串
        """
        if rate is None:
            return "未知"
        return f"{rate * 100:.2f}%"
