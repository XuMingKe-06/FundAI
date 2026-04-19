"""
成本分析师智能体
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from app.agents.base import BaseAgent
from app.data_sources.manager import datasource_manager


logger = logging.getLogger(__name__)


class CostAgent(BaseAgent):
    """成本分析师智能体"""
    
    # 默认赎回费率阶梯（行业标准，不同基金可能有差异）
    DEFAULT_REDEMPTION_LADDER = [
        {"min_days": 0, "max_days": 7, "fee_rate": 0.015, "description": "不满7天"},
        {"min_days": 7, "max_days": 30, "fee_rate": 0.0075, "description": "7-30天"},
        {"min_days": 30, "max_days": 365, "fee_rate": 0.005, "description": "30天-1年"},
        {"min_days": 365, "max_days": 730, "fee_rate": 0.0025, "description": "1-2年"},
        {"min_days": 730, "max_days": None, "fee_rate": 0.0, "description": "2年以上"},
    ]
    
    # 默认持有期分析配置
    HOLDING_PERIODS = [
        {"days": 7, "label": "7天"},
        {"days": 15, "label": "15天"},
        {"days": 30, "label": "30天"},
        {"days": 180, "label": "180天"},
        {"days": 365, "label": "1年"},
    ]
    
    # 默认预期毛收益率（用于短线可行性评估）
    DEFAULT_EXPECTED_RETURN = 0.042
    
    def __init__(self):
        super().__init__("cost", "成本分析师")
    
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
        fund_info = context.get("fund_info", {})
        expected_return = context.get("expected_return", self.DEFAULT_EXPECTED_RETURN)
        
        try:
            # 步骤1: 获取费率信息
            self.add_thinking("正在获取基金费率信息...")
            fees_data = await datasource_manager.get_fund_fees(fund_code)
            
            if fees_data is None:
                self.add_thinking("无法从数据源获取费率信息，将使用默认费率进行估算")
                purchase_fee = 0.0015  # 默认申购费率（平台折扣后）
                redemption_ladder = self.DEFAULT_REDEMPTION_LADDER
            else:
                # 解析申购费率
                purchase_fee = self._parse_purchase_fee(fees_data)
                self.add_thinking(f"申购费率原价{self._format_rate(fees_data.get('purchase_fee'))}，"
                                  f"代销平台折扣后{self._format_rate(purchase_fee)}...")
                
                # 解析赎回费率阶梯（数据源可能不提供完整阶梯，使用默认值）
                redemption_ladder = self._parse_redemption_ladder(fees_data)
            
            # 步骤2: 分析赎回费率阶梯
            self.add_thinking("正在分析赎回费率阶梯...")
            ladder_desc = self._format_ladder_description(redemption_ladder)
            self.add_thinking(ladder_desc)
            
            # 步骤3: 构建成本矩阵
            self.add_thinking("正在计算成本矩阵...")
            cost_matrix = self._build_cost_matrix(purchase_fee, redemption_ladder)
            
            # 格式化成本矩阵输出
            cost_summary = self._format_cost_matrix_summary(cost_matrix)
            self.add_thinking(cost_summary)
            
            # 步骤4: 评估短线可行性
            self.add_thinking("正在评估短线可行性...")
            feasibility_result = self._assess_short_term_feasibility(cost_matrix, expected_return)
            self.add_thinking(feasibility_result["analysis_text"])
            
            # 步骤5: 推荐最优持有期
            recommended_period = self._recommend_holding_period(cost_matrix, expected_return)
            
            # 计算综合评分
            score = self._calculate_score(cost_matrix, feasibility_result)
            
            # 生成摘要
            summary = self._generate_summary(feasibility_result, recommended_period)
            
            # 构建详细结果
            self.details = {
                "purchase_fee_rate": purchase_fee,
                "redemption_fee_ladder": redemption_ladder,
                "cost_matrix": cost_matrix,
                "short_term_feasibility": feasibility_result["feasibility"],
                "feasibility_details": feasibility_result,
                "recommended_holding_period": recommended_period,
                "expected_return": expected_return,
            }
            
            self.score = score
            self.summary = summary
            
            self.add_thinking(f"综合评估：{summary}")
            
            return self.to_dict()
            
        except Exception as e:
            logger.error(f"成本分析失败: {e}", exc_info=True)
            self.add_thinking(f"成本分析过程中发生错误: {str(e)}")
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
            # 假设平台折扣为1折
            return float(original_fee) * 0.1
        return 0.0015  # 默认折扣后费率
    
    def _parse_redemption_ladder(self, fees_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析赎回费率阶梯
        
        Args:
            fees_data: 费率数据
            
        Returns:
            赎回费率阶梯列表
        """
        # 数据源通常只提供基础赎回费率，不提供完整阶梯
        # 这里使用默认阶梯，但可以根据数据源返回的赎回费率进行调整
        base_redemption_fee = fees_data.get("redemption_fee")
        
        if base_redemption_fee is not None:
            # 如果数据源提供了赎回费率，调整默认阶梯
            ladder = []
            for item in self.DEFAULT_REDEMPTION_LADDER:
                adjusted_item = item.copy()
                # 根据基础费率等比例调整
                if item["fee_rate"] > 0:
                    ratio = float(base_redemption_fee) / 0.005  # 以30天-1年为基准
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
            成本矩阵列表，包含各持有期的总费率和盈亏平衡点
        """
        cost_matrix = []
        
        for period in self.HOLDING_PERIODS:
            days = period["days"]
            label = period["label"]
            
            # 根据持有天数查找对应的赎回费率
            redemption_fee = self._get_redemption_fee(days, redemption_ladder)
            
            # 计算总费率
            total_fee = purchase_fee + redemption_fee
            
            # 计算盈亏平衡点（需要达到的收益率才能覆盖成本）
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
                # 无上限的情况
                if holding_days >= min_days:
                    return item["fee_rate"]
            else:
                if min_days <= holding_days < max_days:
                    return item["fee_rate"]
        
        # 默认返回最低费率
        return redemption_ladder[-1]["fee_rate"]
    
    def _calculate_breakeven(self, total_fee: float) -> float:
        """
        计算盈亏平衡点
        
        盈亏平衡点 = 总费率 / (1 - 总费率)
        这是因为：实际收益 = 名义收益 * (1 - 总费率)
        要使实际收益 >= 0，需要名义收益 >= 总费率 / (1 - 总费率)
        
        Args:
            total_fee: 总费率
            
        Returns:
            盈亏平衡点（需要达到的收益率）
        """
        if total_fee >= 1:
            return float('inf')  # 费率超过100%，不可能盈利
        
        # 简化计算：盈亏平衡点约等于总费率
        # 更精确的计算考虑了费用对净值的影响
        return total_fee / (1 - total_fee)
    
    def _assess_short_term_feasibility(
        self,
        cost_matrix: List[Dict[str, Any]],
        expected_return: float
    ) -> Dict[str, Any]:
        """
        评估短线可行性
        
        Args:
            cost_matrix: 成本矩阵
            expected_return: 预期毛收益率
            
        Returns:
            可行性评估结果
        """
        # 找出短线持有期（30天以内）
        short_term_periods = [item for item in cost_matrix if item["holding_days"] <= 30]
        
        if not short_term_periods:
            return {
                "feasibility": "无法评估",
                "analysis_text": "缺少短线持有期数据",
                "net_returns": [],
            }
        
        # 计算各短线持有期的净收益率
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
        
        # 判断是否有可行的短线方案
        profitable_options = [nr for nr in net_returns if nr["is_profitable"]]
        
        if not profitable_options:
            feasibility = "不具备成本可行性"
            analysis_text = f"预期毛收益率{self._format_rate(expected_return)}，" \
                            f"扣除持有成本后净收益为负，短线操作成本过高"
        elif len(profitable_options) == len(net_returns):
            feasibility = "具备成本可行性"
            best_option = max(profitable_options, key=lambda x: x["net_return"])
            analysis_text = f"预期毛收益率{self._format_rate(expected_return)}，" \
                            f"扣除{best_option['holding_period']}持有成本后" \
                            f"净收益率{self._format_rate(best_option['net_return'])}，具备成本可行性"
        else:
            feasibility = "部分具备成本可行性"
            best_option = max(profitable_options, key=lambda x: x["net_return"])
            analysis_text = f"预期毛收益率{self._format_rate(expected_return)}，" \
                            f"推荐持有{best_option['holding_period']}，" \
                            f"净收益率{self._format_rate(best_option['net_return'])}"
        
        return {
            "feasibility": feasibility,
            "analysis_text": analysis_text,
            "net_returns": net_returns,
            "profitable_count": len(profitable_options),
            "total_count": len(net_returns),
        }
    
    def _recommend_holding_period(
        self,
        cost_matrix: List[Dict[str, Any]],
        expected_return: float
    ) -> Optional[str]:
        """
        推荐最优持有期
        
        Args:
            cost_matrix: 成本矩阵
            expected_return: 预期毛收益率
            
        Returns:
            推荐的持有期
        """
        if not cost_matrix:
            return None
        
        # 计算各持有期的净收益率
        best_period = None
        best_net_return = float('-inf')
        
        for item in cost_matrix:
            net_return = expected_return - item["total_fee"]
            if net_return > best_net_return:
                best_net_return = net_return
                best_period = item["holding_period"]
        
        return best_period
    
    def _calculate_score(
        self,
        cost_matrix: List[Dict[str, Any]],
        feasibility_result: Dict[str, Any]
    ) -> float:
        """
        计算综合评分
        
        评分标准：
        - 5.0: 短线成本极低，所有持有期都盈利
        - 4.0-4.9: 短线成本可接受，大部分持有期盈利
        - 3.0-3.9: 短线成本中等，部分持有期盈利
        - 2.0-2.9: 短线成本较高，少数持有期盈利
        - 1.0-1.9: 短线成本很高，难以盈利
        - 0.0-0.9: 短线成本极高，无法盈利
        
        Args:
            cost_matrix: 成本矩阵
            feasibility_result: 可行性评估结果
            
        Returns:
            综合评分
        """
        if not feasibility_result.get("net_returns"):
            return 0.0
        
        net_returns = feasibility_result["net_returns"]
        profitable_count = feasibility_result.get("profitable_count", 0)
        total_count = feasibility_result.get("total_count", len(net_returns))
        
        if total_count == 0:
            return 0.0
        
        # 计算盈利比例
        profit_ratio = profitable_count / total_count
        
        # 计算平均净收益率
        avg_net_return = sum(nr["net_return"] for nr in net_returns) / len(net_returns)
        
        # 基础评分基于盈利比例
        base_score = profit_ratio * 4.0
        
        # 根据平均净收益率调整
        if avg_net_return > 0.03:
            base_score += 1.0
        elif avg_net_return > 0.02:
            base_score += 0.5
        elif avg_net_return > 0.01:
            base_score += 0.2
        elif avg_net_return < 0:
            base_score -= 0.5
        
        # 限制评分范围
        return round(max(0.0, min(5.0, base_score)), 1)
    
    def _generate_summary(
        self,
        feasibility_result: Dict[str, Any],
        recommended_period: Optional[str]
    ) -> str:
        """
        生成分析摘要
        
        Args:
            feasibility_result: 可行性评估结果
            recommended_period: 推荐持有期
            
        Returns:
            分析摘要
        """
        feasibility = feasibility_result.get("feasibility", "无法评估")
        
        if recommended_period:
            return f"{feasibility}，推荐持有期{recommended_period}"
        else:
            return f"{feasibility}"
    
    def _format_rate(self, rate: Optional[float]) -> str:
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
    
    def _format_ladder_description(self, ladder: List[Dict[str, Any]]) -> str:
        """
        格式化赎回费率阶梯描述
        
        Args:
            ladder: 赎回费率阶梯
            
        Returns:
            格式化后的描述字符串
        """
        parts = []
        for item in ladder:
            desc = item.get("description", "")
            fee = item["fee_rate"]
            parts.append(f"{desc}：{self._format_rate(fee)}")
        return "，".join(parts) + "..."
    
    def _format_cost_matrix_summary(self, cost_matrix: List[Dict[str, Any]]) -> str:
        """
        格式化成本矩阵摘要
        
        Args:
            cost_matrix: 成本矩阵
            
        Returns:
            格式化后的摘要字符串
        """
        parts = []
        for item in cost_matrix[:3]:  # 只显示前3个
            parts.append(f"持有{item['holding_period']}总费率{self._format_rate(item['total_fee'])}")
        return "，".join(parts) + "..."
