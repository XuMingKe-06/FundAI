"""
风险分析师测试
"""
import pytest
from unittest.mock import patch
from app.agents.risk import RiskAgent


class TestRiskAgent:
    """RiskAgent测试类"""
    
    def test_risk_agent_init(self):
        """测试初始化"""
        agent = RiskAgent()
        
        assert agent.agent_type == "risk"
        assert agent.name == "风险分析师"
    
    def test_risk_agent_get_tools(self):
        """测试获取工具"""
        agent = RiskAgent()
        tools = agent.get_tools()
        
        tool_names = [t["function"]["name"] for t in tools]
        assert "calculate_volatility" in tool_names or "calculate_max_drawdown" in tool_names
    
    @pytest.mark.asyncio
    async def test_risk_agent_analyze(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试分析方法"""
        agent = RiskAgent()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.analyze("000001", sample_analysis_context)
            
            assert "agent_type" in result
            assert result["agent_type"] == "risk"
