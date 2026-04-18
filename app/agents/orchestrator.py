"""
智能体编排器
"""
import asyncio
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.agents.fundamental import FundamentalAgent
from app.agents.technical import TechnicalAgent
from app.agents.risk import RiskAgent
from app.agents.cost import CostAgent
from app.agents.sentiment import SentimentAgent
from app.agents.decision import DecisionAgent


class AgentOrchestrator:
    """智能体编排器"""
    
    def __init__(self):
        # 初始化所有智能体
        self.analysis_agents: List[BaseAgent] = [
            FundamentalAgent(),
            TechnicalAgent(),
            RiskAgent(),
            CostAgent(),
            SentimentAgent()
        ]
        self.decision_agent = DecisionAgent()
        
        # 智能体结果
        self.agent_results: Dict[str, Any] = {}
    
    async def run_analysis_agents(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """并行运行分析智能体"""
        
        async def run_agent(agent: BaseAgent):
            """运行单个智能体"""
            try:
                if progress_callback:
                    await progress_callback(agent.agent_type, "running", None, None)
                
                result = await agent.run(fund_code, context)
                
                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "completed",
                        agent.score,
                        agent.summary
                    )
                
                return agent.agent_type, result
            except Exception as e:
                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "failed",
                        None,
                        str(e)
                    )
                return agent.agent_type, {"error": str(e)}
        
        # 并行执行所有分析智能体
        tasks = [run_agent(agent) for agent in self.analysis_agents]
        results = await asyncio.gather(*tasks)
        
        # 整理结果
        for agent_type, result in results:
            self.agent_results[agent_type] = result
        
        return self.agent_results
    
    async def run_decision_agent(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """运行决策智能体"""
        
        try:
            if progress_callback:
                await progress_callback("decision", "running", None, None)
            
            # 将分析结果加入上下文
            context["agent_results"] = self.agent_results
            
            result = await self.decision_agent.run(fund_code, context)
            
            if progress_callback:
                await progress_callback(
                    "decision",
                    "completed",
                    None,
                    self.decision_agent.summary
                )
            
            return result
        except Exception as e:
            if progress_callback:
                await progress_callback("decision", "failed", None, str(e))
            return {"error": str(e)}
    
    async def run_full_analysis(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """运行完整分析流程"""
        
        # 第一阶段：并行运行分析智能体
        await self.run_analysis_agents(fund_code, context, progress_callback)
        
        # 第二阶段：运行决策智能体
        decision_result = await self.run_decision_agent(fund_code, context, progress_callback)
        
        # 返回完整结果
        return {
            "analysis_agents": self.agent_results,
            "decision_agent": decision_result,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    def get_agent_thinking_process(self, agent_type: str) -> List[Dict[str, str]]:
        """获取智能体思考过程"""
        if agent_type in self.agent_results:
            return self.agent_results[agent_type].get("thinking_process", [])
        if agent_type == "decision":
            return self.decision_agent.thinking_process
        return []
