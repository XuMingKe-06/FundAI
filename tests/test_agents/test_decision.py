"""
决策智能体测试
"""
import pytest
from unittest.mock import patch
from app.agents.decision import DecisionAgent


class TestDecisionAgent:
    """DecisionAgent测试类"""
    
    def test_decision_agent_init(self):
        """测试初始化"""
        agent = DecisionAgent()
        
        assert agent.agent_type == "decision"
        assert agent.name == "决策智能体"
    
    def test_decision_agent_no_tools(self):
        """测试决策智能体工具配置"""
        agent = DecisionAgent()
        
        assert not hasattr(agent, "_tools") or len(agent.get_tools()) <= 3
    
    def test_decision_agent_no_weights(self):
        """测试无硬编码权重"""
        agent = DecisionAgent()
        
        assert not hasattr(agent, "SHORT_TERM_WEIGHTS")
        assert not hasattr(agent, "LONG_TERM_WEIGHTS")
    
    @pytest.mark.asyncio
    async def test_decision_agent_analyze(self, mock_llm_service, mock_rag_service, sample_agent_results):
        """测试分析方法"""
        agent = DecisionAgent()
        context = {"agent_results": sample_agent_results}
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.analyze("000001", context)
            
            assert "agent_type" in result
            assert result["agent_type"] == "decision"
