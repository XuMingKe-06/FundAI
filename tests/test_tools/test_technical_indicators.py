"""
技术指标工具测试
"""
import pytest
from app.agents.tools.technical_indicators import (
    CalculateMATool,
    CalculateMACDTool,
    CalculateRSITool,
    CalculatePercentileTool
)


class TestCalculateMATool:
    """CalculateMATool测试类"""
    
    def test_calculate_ma_tool_schema(self):
        """测试参数schema"""
        tool = CalculateMATool()
        schema = tool.parameters_schema
        
        assert "values" in schema["properties"]
        assert "period" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_ma_tool(self):
        """测试MA计算"""
        tool = CalculateMATool()
        values = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
                  2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9]
        
        result = await tool.execute(values=values, period=5)
        
        assert result.success is True
        assert "ma_value" in result.data
        assert result.data["ma_value"] > 0
    
    @pytest.mark.asyncio
    async def test_calculate_ma_insufficient_data(self):
        """测试数据不足时MA计算"""
        tool = CalculateMATool()
        values = [1.0, 1.1]
        
        result = await tool.execute(values=values, period=20)
        
        assert result.success is False


class TestCalculateMACDTool:
    """CalculateMACDTool测试类"""
    
    def test_calculate_macd_tool_schema(self):
        """测试参数schema"""
        tool = CalculateMACDTool()
        schema = tool.parameters_schema
        
        assert "values" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_macd_tool(self):
        """测试MACD计算"""
        tool = CalculateMACDTool()
        values = [1.0 + 0.01 * i for i in range(50)]
        
        result = await tool.execute(values=values)
        
        assert result.success is True
        assert "dif" in result.data
        assert "dea" in result.data
        assert "macd_histogram" in result.data
        assert "signal_type" in result.data
    
    @pytest.mark.asyncio
    async def test_calculate_macd_golden_cross(self):
        """测试MACD金叉识别"""
        tool = CalculateMACDTool()
        values = [1.0 - 0.005 * i for i in range(25)] + [1.0 + 0.005 * i for i in range(25)]
        
        result = await tool.execute(values=values)
        
        assert result.success is True
        assert "signal_type" in result.data


class TestCalculateRSITool:
    """CalculateRSITool测试类"""
    
    def test_calculate_rsi_tool_schema(self):
        """测试参数schema"""
        tool = CalculateRSITool()
        schema = tool.parameters_schema
        
        assert "values" in schema["properties"]
        assert "period" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_tool(self):
        """测试RSI计算"""
        tool = CalculateRSITool()
        values = [1.0 + 0.01 * i for i in range(30)]
        
        result = await tool.execute(values=values, period=14)
        
        assert result.success is True
        assert "rsi_value" in result.data
        assert 0 <= result.data["rsi_value"] <= 100
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_oversold(self):
        """测试RSI超卖区间"""
        tool = CalculateRSITool()
        values = [1.5 - 0.02 * i for i in range(30)]
        
        result = await tool.execute(values=values, period=14)
        
        assert result.success is True
        if result.data["rsi_value"] < 30:
            assert result.data["status"] == "超卖"
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_overbought(self):
        """测试RSI超买区间"""
        tool = CalculateRSITool()
        values = [1.0 + 0.03 * i for i in range(30)]
        
        result = await tool.execute(values=values, period=14)
        
        assert result.success is True
        if result.data["rsi_value"] > 70:
            assert result.data["status"] == "超买"


class TestCalculatePercentileTool:
    """CalculatePercentileTool测试类"""
    
    def test_calculate_percentile_tool_schema(self):
        """测试参数schema"""
        tool = CalculatePercentileTool()
        schema = tool.parameters_schema
        
        assert "current_value" in schema["properties"]
        assert "historical_values" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_percentile_tool(self):
        """测试估值分位数计算"""
        tool = CalculatePercentileTool()
        historical = [1.0 + 0.01 * i for i in range(100)]
        current = 1.5
        
        result = await tool.execute(
            current_value=current,
            historical_values=historical
        )
        
        assert result.success is True
        assert "percentile" in result.data
        assert 0 <= result.data["percentile"] <= 100
    
    @pytest.mark.asyncio
    async def test_calculate_percentile_low(self):
        """测试低估值分位数"""
        tool = CalculatePercentileTool()
        historical = [1.5 + 0.01 * i for i in range(100)]
        current = 1.0
        
        result = await tool.execute(
            current_value=current,
            historical_values=historical
        )
        
        assert result.success is True
        assert result.data["percentile"] < 10
    
    @pytest.mark.asyncio
    async def test_calculate_percentile_high(self):
        """测试高估值分位数"""
        tool = CalculatePercentileTool()
        historical = [1.0 + 0.01 * i for i in range(100)]
        current = 2.5
        
        result = await tool.execute(
            current_value=current,
            historical_values=historical
        )
        
        assert result.success is True
        assert result.data["percentile"] > 90
