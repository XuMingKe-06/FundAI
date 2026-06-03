"""
市场数据工具测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.tools.market_data import (
    GetNewsSentimentTool,
    GetFundFlowTool,
    GetSocialHeatTool,
    GetInstitutionalViewsTool,
    GetMarketIndexTool
)


class TestGetNewsSentimentTool:
    """GetNewsSentimentTool测试类"""
    
    def test_get_news_sentiment_tool_schema(self):
        """测试参数schema"""
        tool = GetNewsSentimentTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
        assert "days" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_news_sentiment_tool(self, mock_datasource_manager):
        """测试获取新闻舆情"""
        mock_datasource_manager.get_news_sentiment = AsyncMock(return_value={
            "total": 10,
            "positive": 6,
            "negative": 2,
            "neutral": 2
        })
        
        with patch('app.agents.tools.market_data.datasource_manager', mock_datasource_manager):
            tool = GetNewsSentimentTool()
            result = await tool.execute(fund_code="000001", days=30)
            
            assert result.success is True
            assert "total" in result.data
    
    @pytest.mark.asyncio
    async def test_get_news_sentiment_no_data(self):
        """测试无新闻数据"""
        mock_manager = Mock()
        mock_manager.get_news_sentiment = AsyncMock(return_value=None)
        mock_manager.current_source_name = "test"
        
        with patch('app.agents.tools.market_data.datasource_manager', mock_manager):
            tool = GetNewsSentimentTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is False
            assert result.data is None


class TestGetFundFlowTool:
    """GetFundFlowTool测试类"""
    
    def test_get_fund_flow_tool_schema(self):
        """测试参数schema"""
        tool = GetFundFlowTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_fund_flow_tool(self):
        """测试获取资金流向"""
        mock_manager = Mock()
        mock_manager.get_fund_flow = AsyncMock(return_value={
            "net_inflow_5d": 5.2,
            "net_inflow_20d": 12.5,
            "trend": "流入"
        })
        mock_manager.current_source_name = "test"
        
        with patch('app.agents.tools.market_data.datasource_manager', mock_manager):
            tool = GetFundFlowTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert "net_inflow_5d" in result.data


class TestGetSocialHeatTool:
    """GetSocialHeatTool测试类"""
    
    def test_get_social_heat_tool_schema(self):
        """测试参数schema"""
        tool = GetSocialHeatTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_social_heat_tool(self):
        """测试获取社交热度"""
        mock_manager = Mock()
        mock_manager.get_social_heat = AsyncMock(return_value={
            "heat_ratio": 1.5,
            "level": "high"
        })
        mock_manager.current_source_name = "test"
        
        with patch('app.agents.tools.market_data.datasource_manager', mock_manager):
            tool = GetSocialHeatTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert "heat_ratio" in result.data


class TestGetInstitutionalViewsTool:
    """GetInstitutionalViewsTool测试类"""
    
    def test_get_institutional_views_tool_schema(self):
        """测试参数schema"""
        tool = GetInstitutionalViewsTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_institutional_views_tool(self):
        """测试获取机构观点"""
        mock_manager = Mock()
        mock_manager.get_institutional_views = AsyncMock(return_value={
            "buy": 5,
            "overweight": 3,
            "neutral": 2,
            "underweight": 1,
            "sell": 0
        })
        mock_manager.current_source_name = "test"
        
        with patch('app.agents.tools.market_data.datasource_manager', mock_manager):
            tool = GetInstitutionalViewsTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert "buy" in result.data


class TestGetMarketIndexTool:
    """GetMarketIndexTool测试类"""
    
    def test_get_market_index_tool_schema(self):
        """测试参数schema"""
        tool = GetMarketIndexTool()
        schema = tool.parameters_schema
        
        assert "index_code" in schema["properties"]
        assert "days" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_market_index_tool(self, mock_datasource_manager):
        """测试获取市场指数"""
        with patch('app.agents.tools.market_data.datasource_manager', mock_datasource_manager):
            tool = GetMarketIndexTool()
            result = await tool.execute(index_code="000300", days=30)
            
            assert result.success is True
            assert "index_code" in result.data
            assert "index_name" in result.data
    
    def test_get_index_name(self):
        """测试指数名称获取"""
        tool = GetMarketIndexTool()
        
        assert tool._get_index_name("000300") == "沪深300"
        assert tool._get_index_name("000001") == "上证指数"
        assert tool._get_index_name("999999") == "未知指数"
