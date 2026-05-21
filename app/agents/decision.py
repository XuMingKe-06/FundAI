"""
决策智能体
负责汇总各分析智能体结果，生成综合投资决策建议
"""
from typing import Dict, Any
from loguru import logger
from app.agents.base import BaseAgent

class DecisionAgent(BaseAgent):
    def __init__(self):
        super().__init__("decision", "决策智能体")

    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        agent_results = context.get("agent_results", {})

        insufficient_agents = []
        for agent_type, result in agent_results.items():
            if isinstance(result, dict):
                if result.get("data_sufficient") is False or result.get("data_sufficiency") == "insufficient":
                    insufficient_agents.append(agent_type)

        if insufficient_agents:
            await self.add_thinking(
                f"注意：以下智能体数据不足：{', '.join(insufficient_agents)}，"
                f"决策结论的可靠性可能受影响"
            )
            context["insufficient_agents"] = insufficient_agents

        memory = context.get("memory", {})
        if memory.get("has_history"):
            prev_scores = memory.get("previous_scores", {})
            prev_decision = memory.get("previous_decision", {})
            await self.add_thinking(
                f"检测到历史分析记录（上次分析时间: {memory.get('last_analysis_time', '未知')}），"
                f"将对比历史评分变化"
            )
            if prev_scores:
                score_changes = []
                for agent_type, prev_data in prev_scores.items():
                    prev_score = prev_data.get("score")
                    curr_result = agent_results.get(agent_type, {})
                    curr_score = curr_result.get("score") if isinstance(curr_result, dict) else None
                    if prev_score is not None and curr_score is not None:
                        diff = round(curr_score - prev_score, 2)
                        direction = "上升" if diff > 0 else "下降" if diff < 0 else "持平"
                        score_changes.append(f"{agent_type}: {prev_score}→{curr_score}({direction})")
                if score_changes:
                    await self.add_thinking(f"评分变化: {', '.join(score_changes)}")

        debate_mode = context.get("debate_mode", False)
        if debate_mode:
            debate_round = context.get("debate_round", 0)
            opposing_view = context.get("opposing_view", {})
            disagreement = context.get("disagreement_description", "")
            await self.add_thinking(
                f"辩论第{debate_round}轮 - 对方观点: "
                f"{opposing_view.get('agent_type', '未知')}评分{opposing_view.get('score', '未知')}，"
                f"分歧: {disagreement}"
            )

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
            use_tools=True
        )

        if not self.summary and self.details:
            short_term = self.details.get('short_term_decision', {})
            long_term = self.details.get('long_term_decision', {})

            summary_parts = []
            summary_parts.append("## 综合决策分析完成")
            summary_parts.append("")

            st_direction = short_term.get('direction', 'hold')
            st_direction_map = {'buy': '买入', 'sell': '卖出', 'hold': '持有'}
            summary_parts.append(f"### 短线建议（7-30天）")
            summary_parts.append(f"- 操作方向：{st_direction_map.get(st_direction, '持有')}")
            summary_parts.append(f"- 建议持有期：{short_term.get('holding_period', '暂未确定')}")
            summary_parts.append(f"- 置信度：{short_term.get('confidence', 0) * 100:.0f}%")
            summary_parts.append("")

            lt_direction = long_term.get('direction', 'hold')
            summary_parts.append(f"### 长线建议（6个月以上）")
            summary_parts.append(f"- 操作方向：{st_direction_map.get(lt_direction, '持有')}")
            summary_parts.append(f"- 置信度：{long_term.get('confidence', 0) * 100:.0f}%")
            summary_parts.append(f"- 定投建议：{long_term.get('dip_investment_suggestion', '暂无')}")
            summary_parts.append("")

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

            reasons = short_term.get('reasons', [])
            if reasons:
                summary_parts.append("### 核心依据")
                for i, reason in enumerate(reasons[:3], 1):
                    summary_parts.append(f"{i}. {reason}")

            self.summary = '\n'.join(summary_parts)

        await self.add_thinking("综合决策完成：双轨决策建议已生成。")

        return self.to_dict()
