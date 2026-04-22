"""
成本分析师测试
"""
import pytest
from unittest.mock import patch
from app.agents.cost import CostAgent


class TestCostAgent:
    """CostAgent测试类"""
    
    def test_cost_agent_init(self):
        """测试初始化"""
        agent = CostAgent()
        
        assert agent.agent_type == "cost"
        assert agent.name == "成本分析师"
    
    def test_cost_agent_get_tools(self):
        """测试获取工具"""
        agent = CostAgent()
        tools = agent.get_tools()
        
        tool_names = [t["function"]["name"] for t in tools]
        assert "get_fund_fees" in tool_names
    
    @pytest.mark.asyncio
    async def test_cost_agent_analyze(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试分析方法"""
        agent = CostAgent()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.analyze("000001", sample_analysis_context)
            
            assert "agent_type" in result
            assert result["agent_type"] == "cost"
