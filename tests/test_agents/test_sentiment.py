"""
情绪分析师测试
"""
import pytest
from unittest.mock import patch
from app.agents.sentiment import SentimentAgent


class TestSentimentAgent:
    """SentimentAgent测试类"""
    
    def test_sentiment_agent_init(self):
        """测试初始化"""
        agent = SentimentAgent()
        
        assert agent.agent_type == "sentiment"
        assert agent.name == "情绪分析师"
    
    def test_sentiment_agent_get_tools(self):
        """测试获取工具"""
        agent = SentimentAgent()
        tools = agent.get_tools()
        
        tool_names = [t["function"]["name"] for t in tools]
        assert "get_news_sentiment" in tool_names or "get_fund_flow" in tool_names
    
    def test_sentiment_agent_no_random(self):
        """测试无随机数据生成"""
        import inspect
        source = inspect.getsource(SentimentAgent)
        
        assert "random" not in source.lower() or "import random" not in source
    
    @pytest.mark.asyncio
    async def test_sentiment_agent_analyze(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试分析方法"""
        agent = SentimentAgent()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.analyze("000001", sample_analysis_context)
            
            assert "agent_type" in result
            assert result["agent_type"] == "sentiment"
