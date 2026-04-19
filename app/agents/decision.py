"""
决策智能体
负责汇总各分析智能体结果，生成综合投资决策建议
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import logging

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """决策智能体"""
    
    # 短线决策权重配置
    SHORT_TERM_WEIGHTS = {
        "technical": 0.40,
        "sentiment": 0.30,
        "risk": 0.20,
        "cost": 0.10
    }
    
    # 长线决策权重配置
    LONG_TERM_WEIGHTS = {
        "fundamental": 0.50,
        "technical": 0.30,
        "risk": 0.20
    }
    
    # 持有期与成本矩阵映射
    HOLDING_PERIOD_COST_MAP = {
        "7天": 7,
        "15天": 15,
        "30天": 30,
        "90天": 90,
        "180天": 180,
        "1年": 365
    }
    
    def __init__(self):
        super().__init__("decision", "决策智能体")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行决策分析
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，包含：
                - agent_results: 各智能体的分析结果
                - user_preference: 用户风险偏好（conservative/neutral/aggressive）
                
        Returns:
            决策分析结果字典
        """
        agent_results = context.get("agent_results", {})
        user_preference = context.get("user_preference", "neutral")
        
        # 获取各智能体结果
        fundamental = agent_results.get("fundamental", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        cost = agent_results.get("cost", {})
        sentiment = agent_results.get("sentiment", {})
        
        # 汇总各智能体结果
        self.add_thinking("正在汇总各分析智能体结果...")
        await asyncio.sleep(0.3)
        
        # 提取各智能体评分
        fundamental_score = fundamental.get("score", 3.0)
        technical_score = technical.get("score", 3.0)
        risk_score = risk.get("score", 3.0)
        cost_score = cost.get("score", 3.0)
        sentiment_score = sentiment.get("score", 0.0)
        
        # 将情绪评分从-5~+5转换为1~5
        sentiment_normalized = self._normalize_sentiment_score(sentiment_score)
        
        # 输出汇总信息
        self._log_scores_summary(
            fundamental_score, technical_score, risk_score, 
            cost_score, sentiment_score, sentiment_normalized
        )
        await asyncio.sleep(0.3)
        
        # 计算短线综合得分
        self.add_thinking("正在计算短线综合得分...")
        await asyncio.sleep(0.3)
        
        short_term_score = self._calculate_short_term_score(agent_results)
        self.add_thinking(
            f"短线得分 = 技术面{technical_score}*{self.SHORT_TERM_WEIGHTS['technical']} + "
            f"情绪{sentiment_normalized}*{self.SHORT_TERM_WEIGHTS['sentiment']} + "
            f"风险{risk_score}*{self.SHORT_TERM_WEIGHTS['risk']} + "
            f"成本{cost_score}*{self.SHORT_TERM_WEIGHTS['cost']} = {short_term_score:.2f}"
        )
        await asyncio.sleep(0.3)
        
        # 计算长线综合得分
        self.add_thinking("正在计算长线综合得分...")
        await asyncio.sleep(0.3)
        
        long_term_score = self._calculate_long_term_score(agent_results)
        self.add_thinking(
            f"长线得分 = 基本面{fundamental_score}*{self.LONG_TERM_WEIGHTS['fundamental']} + "
            f"技术面{technical_score}*{self.LONG_TERM_WEIGHTS['technical']} + "
            f"风险{risk_score}*{self.LONG_TERM_WEIGHTS['risk']} = {long_term_score:.2f}"
        )
        await asyncio.sleep(0.3)
        
        # 生成短线决策
        self.add_thinking("正在生成短线决策建议...")
        await asyncio.sleep(0.3)
        
        short_term_decision = self._generate_short_term_decision(
            agent_results, short_term_score, user_preference
        )
        self.add_thinking(
            f"短线建议：{short_term_decision['direction']}，"
            f"建议持有期{short_term_decision['holding_period']}，"
            f"置信度{short_term_decision['confidence']*100:.0f}%"
        )
        await asyncio.sleep(0.3)
        
        # 生成长线决策
        self.add_thinking("正在生成长线决策建议...")
        await asyncio.sleep(0.3)
        
        long_term_decision = self._generate_long_term_decision(
            agent_results, long_term_score, user_preference
        )
        self.add_thinking(
            f"长线建议：{long_term_decision['direction']}，"
            f"置信度{long_term_decision['confidence']*100:.0f}%，"
            f"{'可考虑定投' if long_term_decision.get('dip_investment_suggestion') else ''}"
        )
        await asyncio.sleep(0.3)
        
        # 生成走势预测数据
        self.add_thinking("正在生成走势预测数据...")
        await asyncio.sleep(0.3)
        
        trend_data = self._generate_trend_data(agent_results, fund_code)
        self.add_thinking("历史走势数据已整理，预测走势数据已生成...")
        await asyncio.sleep(0.3)
        
        # 计算评分（决策智能体不单独评分）
        self.score = None
        self.summary = "综合研判完成，生成双轨决策"
        
        # 构建详细信息
        self.details = {
            "short_term_decision": short_term_decision,
            "long_term_decision": long_term_decision,
            "agent_scores": {
                "fundamental": fundamental_score,
                "technical": technical_score,
                "risk": risk_score,
                "cost": cost_score,
                "sentiment": sentiment_score
            },
            "user_preference": user_preference,
            "trend_data": trend_data
        }
        
        self.add_thinking("综合决策完成：双轨决策建议已生成。")
        
        return self.to_dict()
    
    def _normalize_sentiment_score(self, sentiment_score: float) -> float:
        """
        将情绪评分从-5~+5转换为1~5
        
        Args:
            sentiment_score: 原始情绪评分（-5到+5）
            
        Returns:
            归一化后的评分（1到5）
        """
        # 线性映射：-5 -> 1, 0 -> 3, +5 -> 5
        normalized = 3.0 + sentiment_score * 0.4
        return max(1.0, min(5.0, normalized))
    
    def _log_scores_summary(
        self,
        fundamental_score: float,
        technical_score: float,
        risk_score: float,
        cost_score: float,
        sentiment_score: float,
        sentiment_normalized: float
    ) -> None:
        """输出评分汇总信息"""
        risk_level = self._get_risk_level_desc(risk_score)
        cost_feasibility = self._get_cost_feasibility_desc(cost_score)
        
        self.add_thinking(
            f"基本面评分{fundamental_score}，技术面评分{technical_score}，"
            f"风险等级{risk_level}，成本{cost_feasibility}，"
            f"情绪{sentiment_score:+.1f}(归一化{sentiment_normalized:.1f})..."
        )
    
    def _get_risk_level_desc(self, risk_score: float) -> str:
        """根据风险评分获取风险等级描述"""
        if risk_score >= 4.0:
            return "低"
        elif risk_score >= 3.0:
            return "中"
        else:
            return "高"
    
    def _get_cost_feasibility_desc(self, cost_score: float) -> str:
        """根据成本评分获取成本可行性描述"""
        if cost_score >= 4.0:
            return "可行"
        elif cost_score >= 3.0:
            return "部分可行"
        else:
            return "不可行"
    
    def _calculate_short_term_score(self, agent_results: Dict[str, Any]) -> float:
        """
        计算短线综合得分
        
        权重：技术面40%、情绪30%、风险20%、成本10%
        
        Args:
            agent_results: 各智能体分析结果
            
        Returns:
            短线综合得分（1-5）
        """
        technical = agent_results.get("technical", {})
        sentiment = agent_results.get("sentiment", {})
        risk = agent_results.get("risk", {})
        cost = agent_results.get("cost", {})
        
        # 获取各维度评分
        technical_score = technical.get("score", 3.0)
        sentiment_raw = sentiment.get("score", 0.0)
        risk_score = risk.get("score", 3.0)
        cost_score = cost.get("score", 3.0)
        
        # 情绪评分归一化
        sentiment_normalized = self._normalize_sentiment_score(sentiment_raw)
        
        # 加权计算
        weighted_score = (
            technical_score * self.SHORT_TERM_WEIGHTS["technical"] +
            sentiment_normalized * self.SHORT_TERM_WEIGHTS["sentiment"] +
            risk_score * self.SHORT_TERM_WEIGHTS["risk"] +
            cost_score * self.SHORT_TERM_WEIGHTS["cost"]
        )
        
        return round(weighted_score, 2)
    
    def _calculate_long_term_score(self, agent_results: Dict[str, Any]) -> float:
        """
        计算长线综合得分
        
        权重：基本面50%、技术面30%、风险20%
        
        Args:
            agent_results: 各智能体分析结果
            
        Returns:
            长线综合得分（1-5）
        """
        fundamental = agent_results.get("fundamental", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        
        # 获取各维度评分
        fundamental_score = fundamental.get("score", 3.0)
        technical_score = technical.get("score", 3.0)
        risk_score = risk.get("score", 3.0)
        
        # 加权计算
        weighted_score = (
            fundamental_score * self.LONG_TERM_WEIGHTS["fundamental"] +
            technical_score * self.LONG_TERM_WEIGHTS["technical"] +
            risk_score * self.LONG_TERM_WEIGHTS["risk"]
        )
        
        return round(weighted_score, 2)
    
    def _determine_direction(self, score: float) -> str:
        """
        根据得分确定操作方向
        
        Args:
            score: 综合得分（1-5）
            
        Returns:
            操作方向（buy/hold/sell）
        """
        if score >= 3.5:
            return "buy"
        elif score >= 2.5:
            return "hold"
        else:
            return "sell"
    
    def _calculate_confidence(
        self, 
        score: float, 
        agent_results: Dict[str, Any]
    ) -> float:
        """
        计算置信度
        
        置信度基于：
        1. 综合得分偏离中性的程度
        2. 各智能体评分的一致性
        
        Args:
            score: 综合得分
            agent_results: 各智能体分析结果
            
        Returns:
            置信度（0-1）
        """
        # 基础置信度：得分偏离中性（3分）的程度
        deviation = abs(score - 3.0)
        base_confidence = min(0.8, deviation / 2.0)
        
        # 收集各智能体评分
        scores = []
        for agent_name in ["fundamental", "technical", "risk", "cost"]:
            agent_data = agent_results.get(agent_name, {})
            agent_score = agent_data.get("score", 3.0)
            scores.append(agent_score)
        
        # 情绪评分归一化后加入
        sentiment_raw = agent_results.get("sentiment", {}).get("score", 0.0)
        sentiment_normalized = self._normalize_sentiment_score(sentiment_raw)
        scores.append(sentiment_normalized)
        
        # 计算评分一致性（标准差越小，一致性越高）
        if len(scores) > 1:
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5
            
            # 一致性调整：标准差越小，置信度越高
            consistency_factor = max(0.5, 1.0 - std_dev / 2.0)
        else:
            consistency_factor = 0.7
        
        # 最终置信度
        confidence = base_confidence * consistency_factor + 0.15
        
        # 限制在合理范围内
        return round(min(0.95, max(0.3, confidence)), 2)
    
    def _generate_short_term_decision(
        self,
        agent_results: Dict[str, Any],
        short_term_score: float,
        user_preference: str
    ) -> Dict[str, Any]:
        """
        生成短线决策建议
        
        Args:
            agent_results: 各智能体分析结果
            short_term_score: 短线综合得分
            user_preference: 用户风险偏好
            
        Returns:
            短线决策字典
        """
        cost = agent_results.get("cost", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        sentiment = agent_results.get("sentiment", {})
        
        # 前置条件检查：成本可行性判断
        cost_feasibility = cost.get("details", {}).get("short_term_feasibility", "无法评估")
        cost_details = cost.get("details", {}).get("feasibility_details", {})
        
        # 根据成本可行性调整决策
        if cost_feasibility == "不具备成本可行性":
            # 成本不可行，建议持有更长时间
            direction = "hold"
            holding_period = cost.get("details", {}).get("recommended_holding_period", "30天")
            self.add_thinking("短线成本不可行，建议延长持有期...")
        else:
            # 确定操作方向
            direction = self._determine_direction(short_term_score)
            
            # 根据成本矩阵推荐持有期
            holding_period = self._determine_holding_period(cost, short_term_score)
        
        # 计算置信度
        confidence = self._calculate_confidence(short_term_score, agent_results)
        
        # 生成决策理由
        reasons = self._generate_short_term_reasons(agent_results, direction)
        
        # 生成止盈止损参考
        stop_profit, stop_loss = self._generate_stop_levels(
            agent_results, direction, user_preference
        )
        
        return {
            "direction": direction,
            "holding_period": holding_period,
            "confidence": confidence,
            "reasons": reasons,
            "stop_profit": stop_profit,
            "stop_loss": stop_loss,
            "cost_feasibility": cost_feasibility
        }
    
    def _determine_holding_period(
        self, 
        cost: Dict[str, Any], 
        score: float
    ) -> str:
        """
        根据成本矩阵和得分确定推荐持有期
        
        Args:
            cost: 成本分析结果
            score: 综合得分
            
        Returns:
            推荐持有期
        """
        cost_matrix = cost.get("details", {}).get("cost_matrix", [])
        recommended = cost.get("details", {}).get("recommended_holding_period", "15天")
        
        if not cost_matrix:
            return recommended
        
        # 根据得分调整持有期
        if score >= 4.0:
            # 高分，可以选择较短的持有期
            for item in cost_matrix:
                if item.get("holding_days", 0) >= 15:
                    return item.get("holding_period", "15天")
        elif score >= 3.0:
            # 中等得分，选择推荐持有期
            return recommended
        else:
            # 低分，建议较长持有期以降低成本影响
            for item in cost_matrix:
                if item.get("holding_days", 0) >= 30:
                    return item.get("holding_period", "30天")
        
        return recommended
    
    def _generate_short_term_reasons(
        self,
        agent_results: Dict[str, Any],
        direction: str
    ) -> List[str]:
        """
        生成短线决策理由
        
        Args:
            agent_results: 各智能体分析结果
            direction: 操作方向
            
        Returns:
            决策理由列表
        """
        reasons = []
        
        technical = agent_results.get("technical", {})
        technical_details = technical.get("details", {})
        technical_score = technical.get("score", 3.0)
        
        # 技术面理由
        trend = technical_details.get("trend_direction", "震荡")
        macd_signal = technical_details.get("macd_signal", "")
        rsi = technical_details.get("rsi_14")
        
        if direction == "buy":
            if trend == "上升":
                reasons.append("技术面趋势向上")
            if macd_signal in ["金叉", "多头"]:
                reasons.append(f"MACD{macd_signal}信号")
            if rsi and rsi < 40:
                reasons.append("RSI处于相对低位")
        elif direction == "sell":
            if trend == "下降":
                reasons.append("技术面趋势向下")
            if macd_signal in ["死叉", "空头"]:
                reasons.append(f"MACD{macd_signal}信号")
            if rsi and rsi > 60:
                reasons.append("RSI处于相对高位")
        else:
            reasons.append(f"技术面呈{trend}态势")
        
        # 成本理由
        cost = agent_results.get("cost", {})
        cost_details = cost.get("details", {})
        total_fee = None
        cost_matrix = cost_details.get("cost_matrix", [])
        if cost_matrix:
            for item in cost_matrix:
                if item.get("holding_days", 0) == 15:
                    total_fee = item.get("total_fee")
                    break
        
        if total_fee is not None:
            reasons.append(f"总费率{total_fee*100:.2f}%")
        
        # 情绪理由
        sentiment = agent_results.get("sentiment", {})
        sentiment_score = sentiment.get("score", 0)
        if sentiment_score > 1:
            reasons.append("市场情绪偏正面")
        elif sentiment_score < -1:
            reasons.append("市场情绪偏负面")
        
        # 如果没有生成理由，添加默认理由
        if not reasons:
            reasons.append("综合各维度分析")
        
        return reasons[:5]  # 最多返回5条理由
    
    def _generate_stop_levels(
        self,
        agent_results: Dict[str, Any],
        direction: str,
        user_preference: str
    ) -> Tuple[str, str]:
        """
        生成止盈止损参考
        
        Args:
            agent_results: 各智能体分析结果
            direction: 操作方向
            user_preference: 用户风险偏好
            
        Returns:
            (止盈参考, 止损参考)
        """
        risk = agent_results.get("risk", {})
        risk_details = risk.get("details", {})
        
        # 获取风险指标
        max_drawdown = risk_details.get("max_drawdown", 15)
        volatility = risk_details.get("annual_volatility", 20)
        
        # 根据风险偏好调整止盈止损比例
        if user_preference == "conservative":
            stop_profit_ratio = 0.6
            stop_loss_ratio = 0.5
        elif user_preference == "aggressive":
            stop_profit_ratio = 1.2
            stop_loss_ratio = 1.0
        else:
            stop_profit_ratio = 0.8
            stop_loss_ratio = 0.7
        
        # 计算止盈止损参考
        if direction == "buy":
            # 基于波动率计算预期收益
            expected_profit = volatility * 0.15 * stop_profit_ratio
            stop_profit = f"预期收益率{expected_profit:.1f}%"
            
            # 基于最大回撤计算止损
            stop_loss_value = max_drawdown * stop_loss_ratio
            stop_loss = f"最大回撤{stop_loss_value:.1f}%"
        elif direction == "sell":
            stop_profit = "已止盈/止损"
            stop_loss = "建议观望"
        else:
            stop_profit = f"预期收益率{volatility * 0.1:.1f}%"
            stop_loss = f"最大回撤{max_drawdown * 0.6:.1f}%"
        
        return stop_profit, stop_loss
    
    def _generate_long_term_decision(
        self,
        agent_results: Dict[str, Any],
        long_term_score: float,
        user_preference: str
    ) -> Dict[str, Any]:
        """
        生成长线决策建议
        
        Args:
            agent_results: 各智能体分析结果
            long_term_score: 长线综合得分
            user_preference: 用户风险偏好
            
        Returns:
            长线决策字典
        """
        fundamental = agent_results.get("fundamental", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        
        # 确定操作方向
        direction = self._determine_direction(long_term_score)
        
        # 计算置信度
        confidence = self._calculate_confidence(long_term_score, agent_results)
        
        # 生成决策理由
        reasons = self._generate_long_term_reasons(agent_results, direction)
        
        # 判断是否触发定投建议条件
        dip_investment_suggestion = None
        if direction == "buy" and long_term_score >= 3.5:
            # 检查估值分位数
            valuation_percentile = technical.get("details", {}).get("valuation_percentile", 50)
            risk_level = risk.get("details", {}).get("risk_level", "中")
            
            if valuation_percentile < 40 and risk_level != "高":
                dip_investment_suggestion = "可考虑分批定投"
            elif long_term_score >= 4.0:
                dip_investment_suggestion = "可考虑分批建仓"
        
        return {
            "direction": direction,
            "confidence": confidence,
            "reasons": reasons,
            "dip_investment_suggestion": dip_investment_suggestion
        }
    
    def _generate_long_term_reasons(
        self,
        agent_results: Dict[str, Any],
        direction: str
    ) -> List[str]:
        """
        生成长线决策理由
        
        Args:
            agent_results: 各智能体分析结果
            direction: 操作方向
            
        Returns:
            决策理由列表
        """
        reasons = []
        
        fundamental = agent_results.get("fundamental", {})
        fundamental_details = fundamental.get("details", {})
        fundamental_score = fundamental.get("score", 3.0)
        
        # 基本面理由
        manager_name = fundamental_details.get("fund_manager", "未知")
        experience_years = fundamental_details.get("management_experience_years", 0)
        alpha_1y = fundamental_details.get("alpha_1y", 0)
        
        if direction == "buy":
            reasons.append(f"基本面评分{fundamental_score}分")
            if experience_years >= 5:
                reasons.append(f"基金经理{manager_name}从业{experience_years}年，经验丰富")
            if alpha_1y > 0:
                reasons.append(f"近1年超额收益{alpha_1y:.2f}%")
        elif direction == "sell":
            if fundamental_score < 2.5:
                reasons.append("基本面评分较低")
            if alpha_1y < 0:
                reasons.append(f"近1年跑输基准{abs(alpha_1y):.2f}%")
        else:
            reasons.append(f"基本面评分{fundamental_score}分，表现平稳")
        
        # 估值理由
        technical = agent_results.get("technical", {})
        valuation_percentile = technical.get("details", {}).get("valuation_percentile")
        if valuation_percentile is not None:
            if valuation_percentile < 30:
                reasons.append("估值处于历史低位，安全边际较高")
            elif valuation_percentile > 70:
                reasons.append("估值处于历史高位，需谨慎")
        
        # 持仓结构理由
        industry_concentration = fundamental_details.get("industry_concentration", "")
        if industry_concentration and industry_concentration != "未知":
            reasons.append(f"持仓以{industry_concentration}为主")
        
        # 如果没有生成理由，添加默认理由
        if not reasons:
            reasons.append("综合基本面和技术面分析")
        
        return reasons[:5]  # 最多返回5条理由
    
    def _generate_trend_data(
        self,
        agent_results: Dict[str, Any],
        fund_code: str
    ) -> Dict[str, Any]:
        """
        生成走势预测数据
        
        Args:
            agent_results: 各智能体分析结果
            fund_code: 基金代码
            
        Returns:
            走势数据字典，包含历史走势和预测走势
        """
        technical = agent_results.get("technical", {})
        technical_details = technical.get("details", {})
        
        # 获取技术分析数据
        current_nav = technical_details.get("current_nav", 1.0)
        ma20 = technical_details.get("ma20", current_nav)
        ma60 = technical_details.get("ma60", current_nav)
        macd_signal = technical_details.get("macd_signal", "震荡")
        prediction_15d = technical_details.get("prediction_15d", {})
        valuation_percentile = technical_details.get("valuation_percentile", 50)
        
        # 生成历史走势数据（模拟，基于当前净值和技术指标）
        historical_trend = self._generate_historical_trend(
            current_nav, ma20, ma60, valuation_percentile
        )
        
        # 生成预测走势数据
        predicted_trend = self._generate_predicted_trend(
            current_nav, macd_signal, prediction_15d, valuation_percentile
        )
        
        return {
            "historical": historical_trend,
            "predicted": predicted_trend,
            "current_nav": round(current_nav, 4) if current_nav else None,
            "prediction_direction": prediction_15d.get("direction", "震荡")
        }
    
    def _generate_historical_trend(
        self,
        current_nav: float,
        ma20: Optional[float],
        ma60: Optional[float],
        valuation_percentile: float
    ) -> List[Dict[str, Any]]:
        """
        生成历史走势数据
        
        基于技术分析结果反向推算历史走势
        
        Args:
            current_nav: 当前净值
            ma20: 20日均线
            ma60: 60日均线
            valuation_percentile: 估值分位数
            
        Returns:
            历史走势数据列表
        """
        historical = []
        today = datetime.now()
        
        # 生成近60天的历史数据
        for i in range(60, 0, -1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            
            # 基于均线关系推算历史净值
            if ma20 and ma60:
                # 计算历史净值相对于当前的变化
                if i > 40:
                    # 更早的数据，参考MA60
                    ratio = 0.95 + (ma60 / current_nav - 0.95) * (i - 40) / 20
                elif i > 20:
                    # 中间数据，参考MA20
                    ratio = 0.97 + (ma20 / current_nav - 0.97) * (i - 20) / 20
                else:
                    # 近期数据，逐渐接近当前净值
                    ratio = 0.99 + 0.01 * (20 - i) / 20
            else:
                # 无均线数据，使用估值分位数推算
                ratio = 0.95 + (valuation_percentile / 100) * 0.1
            
            # 添加随机波动
            import random
            random.seed(i)  # 固定种子保证可重复性
            noise = random.uniform(-0.02, 0.02)
            
            nav = current_nav * (ratio + noise)
            historical.append({
                "date": date,
                "nav": round(nav, 4)
            })
        
        return historical
    
    def _generate_predicted_trend(
        self,
        current_nav: float,
        macd_signal: str,
        prediction_15d: Dict[str, Any],
        valuation_percentile: float
    ) -> List[Dict[str, Any]]:
        """
        生成预测走势数据
        
        Args:
            current_nav: 当前净值
            macd_signal: MACD信号
            prediction_15d: 15天预测数据
            valuation_percentile: 估值分位数
            
        Returns:
            预测走势数据列表
        """
        predicted = []
        today = datetime.now()
        
        # 获取预测方向和目标区间
        direction = prediction_15d.get("direction", "横盘震荡")
        target_low = prediction_15d.get("target_low", current_nav * 0.98)
        target_high = prediction_15d.get("target_high", current_nav * 1.02)
        
        # 根据方向确定趋势斜率
        if "上行" in direction or macd_signal in ["金叉", "多头"]:
            trend_slope = 0.002  # 每天上涨0.2%
        elif "下行" in direction or macd_signal in ["死叉", "空头"]:
            trend_slope = -0.002  # 每天下跌0.2%
        else:
            trend_slope = 0.0  # 横盘
        
        # 生成未来15天的预测数据
        import random
        random.seed(42)  # 固定种子
        
        for i in range(1, 16):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            
            # 基础趋势
            base_nav = current_nav * (1 + trend_slope * i)
            
            # 添加随机波动（模拟置信区间）
            noise = random.uniform(-0.01, 0.01)
            nav = base_nav * (1 + noise)
            
            # 确保在目标区间内
            nav = max(target_low, min(target_high, nav))
            
            # 计算置信区间（越远越宽）
            confidence_width = 0.01 + 0.005 * i
            upper_bound = nav * (1 + confidence_width)
            lower_bound = nav * (1 - confidence_width)
            
            predicted.append({
                "date": date,
                "nav": round(nav, 4),
                "upper_bound": round(upper_bound, 4),
                "lower_bound": round(lower_bound, 4)
            })
        
        return predicted
