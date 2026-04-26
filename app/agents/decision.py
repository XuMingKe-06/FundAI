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
        
        # 确保决策智能体的 summary 包含完整的结构化信息
        # 如果 LLM 没有返回 summary，则根据 details 生成
        if not self.summary and self.details:
            short_term = self.details.get('short_term_decision', {})
            long_term = self.details.get('long_term_decision', {})
            
            summary_parts = []
            summary_parts.append("## 综合决策分析完成")
            summary_parts.append("")
            
            # 短线决策摘要
            st_direction = short_term.get('direction', 'hold')
            st_direction_map = {'buy': '买入', 'sell': '卖出', 'hold': '持有'}
            summary_parts.append(f"### 短线建议（7-30天）")
            summary_parts.append(f"- 操作方向：{st_direction_map.get(st_direction, '持有')}")
            summary_parts.append(f"- 建议持有期：{short_term.get('holding_period', '暂未确定')}")
            summary_parts.append(f"- 置信度：{short_term.get('confidence', 0) * 100:.0f}%")
            summary_parts.append("")
            
            # 长线决策摘要
            lt_direction = long_term.get('direction', 'hold')
            summary_parts.append(f"### 长线建议（6个月以上）")
            summary_parts.append(f"- 操作方向：{st_direction_map.get(lt_direction, '持有')}")
            summary_parts.append(f"- 置信度：{long_term.get('confidence', 0) * 100:.0f}%")
            summary_parts.append(f"- 定投建议：{long_term.get('dip_investment_suggestion', '暂无')}")
            summary_parts.append("")
            
            # 智能体评分汇总
            agent_scores = self.details.get('agent_scores', {})
            summary_parts.append("### 各维度评分")
            score_names = {
                'fundamental': '基本面',
                'technical': '技术面',
                'risk': '风险',
                'cost': '成本',
                'sentiment': '情绪'
            }
            for key, name in score_names.items():
                score = agent_scores.get(key, '未知')
                summary_parts.append(f"- {name}：{score}分")
            summary_parts.append("")
            
            # 风险提示
            reasons = short_term.get('reasons', [])
            if reasons:
                summary_parts.append("### 核心依据")
                for i, reason in enumerate(reasons[:3], 1):
                    summary_parts.append(f"{i}. {reason}")
            
            self.summary = '\n'.join(summary_parts)
        
        await self.add_thinking("综合决策完成：双轨决策建议已生成。")
        
        return self.to_dict()
