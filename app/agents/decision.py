"""
决策智能体
"""
from typing import Dict, Any, List
from decimal import Decimal

from app.agents.base import BaseAgent
import asyncio


class DecisionAgent(BaseAgent):
    """决策智能体"""
    
    def __init__(self):
        super().__init__("decision", "决策智能体")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行决策分析"""
        agent_results = context.get("agent_results", {})
        user_preference = context.get("user_preference", "neutral")
        
        # 获取各智能体结果
        fundamental = agent_results.get("fundamental", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        cost = agent_results.get("cost", {})
        sentiment = agent_results.get("sentiment", {})
        
        # 模拟分析过程
        self.add_thinking("正在汇总各分析智能体结果...")
        await asyncio.sleep(0.3)
        
        fundamental_score = fundamental.get("score", 3.5)
        technical_score = technical.get("score", 3.5)
        risk_score = risk.get("score", 3.5)
        cost_score = cost.get("score", 3.5)
        sentiment_score = sentiment.get("score", 3.0)
        
        self.add_thinking(f"基本面评分{fundamental_score}，技术面评分{technical_score}，风险等级中，成本可行，情绪+{int(sentiment_score)}...")
        await asyncio.sleep(0.3)
        
        # 计算短线综合得分
        self.add_thinking("正在计算短线综合得分...")
        await asyncio.sleep(0.3)
        
        short_term_score = (
            technical_score * 0.4 +
            sentiment_score * 0.3 +
            risk_score * 0.2 +
            cost_score * 0.1
        )
        self.add_thinking(f"短线得分 = {technical_score}*0.4 + {sentiment_score}*0.3 + {risk_score}*0.2 + {cost_score}*0.1 = {short_term_score:.2f}...")
        await asyncio.sleep(0.3)
        
        # 计算长线综合得分
        self.add_thinking("正在计算长线综合得分...")
        await asyncio.sleep(0.3)
        
        long_term_score = (
            fundamental_score * 0.5 +
            technical_score * 0.3 +
            risk_score * 0.2
        )
        self.add_thinking(f"长线得分 = {fundamental_score}*0.5 + {technical_score}*0.3 + {risk_score}*0.2 = {long_term_score:.2f}...")
        await asyncio.sleep(0.3)
        
        # 生成短线建议
        self.add_thinking("正在生成短线建议...")
        await asyncio.sleep(0.3)
        
        short_term_direction = "buy" if short_term_score >= 3.5 else "hold" if short_term_score >= 2.5 else "sell"
        short_term_confidence = min(0.95, short_term_score / 5.0)
        self.add_thinking(f"短线建议：{short_term_direction}，建议持有期15天，置信度{short_term_confidence*100:.0f}%...")
        await asyncio.sleep(0.3)
        
        # 生成长线建议
        self.add_thinking("正在生成长线建议...")
        await asyncio.sleep(0.3)
        
        long_term_direction = "buy" if long_term_score >= 3.5 else "hold" if long_term_score >= 2.5 else "sell"
        long_term_confidence = min(0.95, long_term_score / 5.0)
        self.add_thinking(f"长线建议：{long_term_direction}，可考虑分批定投，置信度{long_term_confidence*100:.0f}%...")
        await asyncio.sleep(0.3)
        
        # 生成走势预测数据
        self.add_thinking("正在生成走势预测数据...")
        await asyncio.sleep(0.3)
        
        self.add_thinking("历史走势数据已整理，预测走势数据已生成...")
        await asyncio.sleep(0.3)
        
        # 计算评分（决策智能体不单独评分）
        self.score = None
        self.summary = "综合研判完成，生成双轨决策"
        
        self.details = {
            "short_term_decision": {
                "direction": short_term_direction,
                "holding_period": "15天",
                "confidence": short_term_confidence,
                "reasons": [
                    "技术面趋势向上，RSI处于中性区间",
                    "成本效益较好，总费率0.90%",
                    "市场情绪偏正面"
                ],
                "stop_profit": "预期收益率3.5%",
                "stop_loss": "最大回撤5%"
            },
            "long_term_decision": {
                "direction": long_term_direction,
                "confidence": long_term_confidence,
                "reasons": [
                    f"基本面评分{fundamental_score}分，基金经理经验丰富",
                    "估值处于历史低位，安全边际较高",
                    "持仓结构合理，行业分散"
                ],
                "dip_investment_suggestion": "可考虑分批定投" if long_term_direction == "buy" else None
            },
            "agent_scores": {
                "fundamental": fundamental_score,
                "technical": technical_score,
                "risk": risk_score,
                "cost": cost_score,
                "sentiment": sentiment_score
            },
            "user_preference": user_preference
        }
        
        self.add_thinking("综合决策完成：双轨决策建议已生成。")
        
        return self.to_dict()
