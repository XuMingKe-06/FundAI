"""
基金数据工具测试
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.agents.tools.fund_data import (
    GetFundInfoTool,
    GetNavHistoryTool,
    GetHoldingsTool,
    GetFundManagerTool,
    GetFundFeesTool
)


class TestGetFundInfoTool:
    """GetFundInfoTool测试类"""
    
    def test_get_fund_info_tool_schema(self):
        """测试参数schema"""
        tool = GetFundInfoTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
        assert "fund_code" in schema["required"]
    
    def test_get_fund_info_tool_name(self):
        """测试工具名称"""
        tool = GetFundInfoTool()
        assert tool.name == "get_fund_info"
    
    def test_get_fund_info_tool_description(self):
        """测试工具描述"""
        tool = GetFundInfoTool()
        assert "基金基础信息" in tool.description
    
    @pytest.mark.asyncio
    async def test_get_fund_info_tool_execute(self, mock_datasource_manager):
        """测试执行获取基金信息"""
        with patch('app.agents.tools.fund_data.datasource_manager', mock_datasource_manager):
            tool = GetFundInfoTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert result.data is not None
            assert "fund_name" in result.data
    
    @pytest.mark.asyncio
    async def test_get_fund_info_tool_invalid_code(self):
        """测试无效基金代码"""
        mock_manager = Mock()
        mock_manager.get_fund_info = AsyncMock(return_value=None)
        mock_manager.current_source_name = "test"
        
        with patch('app.agents.tools.fund_data.datasource_manager', mock_manager):
            tool = GetFundInfoTool()
            result = await tool.execute(fund_code="invalid")
            
            assert result.success is False


class TestGetNavHistoryTool:
    """GetNavHistoryTool测试类"""
    
    def test_get_nav_history_tool_schema(self):
        """测试参数schema"""
        tool = GetNavHistoryTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
        assert "start_date" in schema["properties"]
        assert "end_date" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_nav_history_tool_execute(self, mock_datasource_manager):
        """测试执行获取净值历史"""
        with patch('app.agents.tools.fund_data.datasource_manager', mock_datasource_manager):
            tool = GetNavHistoryTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert isinstance(result.data, list)


class TestGetHoldingsTool:
    """GetHoldingsTool测试类"""
    
    def test_get_holdings_tool_schema(self):
        """测试参数schema"""
        tool = GetHoldingsTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_holdings_tool_execute(self, mock_datasource_manager):
        """测试执行获取持仓信息"""
        with patch('app.agents.tools.fund_data.datasource_manager', mock_datasource_manager):
            tool = GetHoldingsTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert result.data is not None


class TestGetFundManagerTool:
    """GetFundManagerTool测试类"""
    
    def test_get_fund_manager_tool_schema(self):
        """测试参数schema"""
        tool = GetFundManagerTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_fund_manager_tool_execute(self, mock_datasource_manager):
        """测试执行获取基金经理信息"""
        with patch('app.agents.tools.fund_data.datasource_manager', mock_datasource_manager):
            tool = GetFundManagerTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert "manager_name" in result.data


class TestGetFundFeesTool:
    """GetFundFeesTool测试类"""
    
    def test_get_fund_fees_tool_schema(self):
        """测试参数schema"""
        tool = GetFundFeesTool()
        schema = tool.parameters_schema
        
        assert "fund_code" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_fund_fees_tool_execute(self, mock_datasource_manager):
        """测试执行获取费率信息"""
        with patch('app.agents.tools.fund_data.datasource_manager', mock_datasource_manager):
            tool = GetFundFeesTool()
            result = await tool.execute(fund_code="000001")
            
            assert result.success is True
            assert "purchase_fee_rate" in result.data
