"""
基本面分析师测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.fundamental import FundamentalAgent


class TestFundamentalAgent:
    """FundamentalAgent测试类"""
    
    def test_fundamental_agent_init(self):
        """测试初始化"""
        agent = FundamentalAgent()
        
        assert agent.agent_type == "fundamental"
        assert agent.name == "基本面分析师"
    
    def test_fundamental_agent_get_tools(self):
        """测试获取工具"""
        agent = FundamentalAgent()
        tools = agent.get_tools()
        
        tool_names = [t["function"]["name"] for t in tools]
        assert "get_fund_info" in tool_names
    
    def test_fundamental_agent_no_hardcoded_score(self):
        """测试无硬编码评分方法"""
        agent = FundamentalAgent()
        
        assert not hasattr(agent, "_calculate_weighted_score")
        assert not hasattr(agent, "_calculate_score")
    
    @pytest.mark.asyncio
    async def test_fundamental_agent_analyze(self, mock_rag_service, sample_analysis_context):
        """测试分析方法"""
        agent = FundamentalAgent()
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"score": 3.5, "summary": "测试", "details": {}}', tool_calls=None))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mock_llm_service = Mock()
        mock_llm_service.get_async_client = Mock(return_value=mock_client)
        mock_llm_service.get_model_name = Mock(return_value="test-model")
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.analyze("000001", sample_analysis_context)
            
            assert "agent_type" in result
            assert result["agent_type"] == "fundamental"
