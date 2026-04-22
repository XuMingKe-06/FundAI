"""
决策智能体
负责汇总各分析智能体结果，生成综合投资决策建议
"""
from typing import Dict, Any
import logging

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """决策智能体
    
    通过LLM驱动的方式汇总各分析智能体结果，
    生成短线（<=30天）与长线（>=6个月）两套独立决策建议。
    """
    
    def __init__(self):
        super().__init__("decision", "决策智能体")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行决策分析
        
        通过LLM汇总各分析智能体结果，生成双轨投资决策建议。
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，包含：
                - agent_results: 各智能体的分析结果
                - user_preference: 用户风险偏好（conservative/neutral/aggressive）
                - fund_info: 基金基础信息
                
        Returns:
            决策分析结果字典
        """
        agent_results = context.get("agent_results", {})
        
        await self.add_thinking("正在汇总各分析智能体结果...")
        
        await self.add_thinking(
            f"基本面评分：{agent_results.get('fundamental', {}).get('score', '未知')}，"
            f"技术面评分：{agent_results.get('technical', {}).get('score', '未知')}，"
            f"风险评分：{agent_results.get('risk', {}).get('score', '未知')}，"
            f"成本评分：{agent_results.get('cost', {}).get('score', '未知')}，"
            f"情绪评分：{agent_results.get('sentiment', {}).get('score', '未知')}"
        )
        
        await self.add_thinking("正在调用大语言模型进行综合研判...")
        
        result = await self.run_llm_analysis(
            fund_code=fund_code,
            context=context,
            use_rag=True,
            use_tools=False
        )
        
        await self.add_thinking("综合决策完成：双轨决策建议已生成。")
        
        return self.to_dict()
