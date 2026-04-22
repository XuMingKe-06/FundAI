"""
风险指标工具测试
"""
import pytest
import numpy as np
from app.agents.tools.risk_metrics import (
    CalculateVolatilityTool,
    CalculateMaxDrawdownTool,
    CalculateSharpeRatioTool,
    CalculateBetaTool
)


class TestCalculateVolatilityTool:
    """CalculateVolatilityTool测试类"""
    
    def test_calculate_volatility_tool_schema(self):
        """测试参数schema"""
        tool = CalculateVolatilityTool()
        schema = tool.parameters_schema
        
        assert "nav_values" in schema["properties"]
        assert "annualization_factor" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_tool(self):
        """测试波动率计算"""
        tool = CalculateVolatilityTool()
        nav_values = [1.0 + 0.01 * np.sin(i * 0.1) for i in range(100)]
        
        result = await tool.execute(nav_values=nav_values)
        
        assert result.success is True
        assert "annual_volatility" in result.data
        assert result.data["annual_volatility"] >= 0
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_insufficient_data(self):
        """测试数据不足时波动率计算"""
        tool = CalculateVolatilityTool()
        nav_values = [1.0]
        
        result = await tool.execute(nav_values=nav_values)
        
        assert result.success is False


class TestCalculateMaxDrawdownTool:
    """CalculateMaxDrawdownTool测试类"""
    
    def test_calculate_max_drawdown_tool_schema(self):
        """测试参数schema"""
        tool = CalculateMaxDrawdownTool()
        schema = tool.parameters_schema
        
        assert "nav_values" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_max_drawdown_tool(self):
        """测试最大回撤计算"""
        tool = CalculateMaxDrawdownTool()
        nav_values = [1.0, 1.1, 1.2, 1.1, 1.0, 0.9, 1.0, 1.1, 1.2, 1.3]
        
        result = await tool.execute(nav_values=nav_values)
        
        assert result.success is True
        assert "max_drawdown" in result.data
        assert result.data["max_drawdown"] >= 0
        assert "start_index" in result.data
        assert "end_index" in result.data
    
    @pytest.mark.asyncio
    async def test_calculate_max_drawdown_no_drawdown(self):
        """测试无回撤情况"""
        tool = CalculateMaxDrawdownTool()
        nav_values = [1.0 + 0.01 * i for i in range(20)]
        
        result = await tool.execute(nav_values=nav_values)
        
        assert result.success is True
        assert result.data["max_drawdown"] >= 0


class TestCalculateSharpeRatioTool:
    """CalculateSharpeRatioTool测试类"""
    
    def test_calculate_sharpe_ratio_tool_schema(self):
        """测试参数schema"""
        tool = CalculateSharpeRatioTool()
        schema = tool.parameters_schema
        
        assert "nav_values" in schema["properties"]
        assert "risk_free_rate" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_tool(self):
        """测试夏普比率计算"""
        tool = CalculateSharpeRatioTool()
        nav_values = [1.0 + 0.002 * i + 0.001 * np.sin(i) for i in range(100)]
        
        result = await tool.execute(nav_values=nav_values, risk_free_rate=0.02)
        
        assert result.success is True
        assert "sharpe_ratio" in result.data
        assert "annual_return" in result.data
        assert "annual_volatility" in result.data
    
    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_negative(self):
        """测试负收益时夏普比率"""
        tool = CalculateSharpeRatioTool()
        nav_values = [1.5 - 0.005 * i for i in range(100)]
        
        result = await tool.execute(nav_values=nav_values, risk_free_rate=0.02)
        
        assert result.success is True
        assert result.data["sharpe_ratio"] < 0


class TestCalculateBetaTool:
    """CalculateBetaTool测试类"""
    
    def test_calculate_beta_tool_schema(self):
        """测试参数schema"""
        tool = CalculateBetaTool()
        schema = tool.parameters_schema
        
        assert "fund_nav_values" in schema["properties"]
        assert "benchmark_nav_values" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_calculate_beta_tool(self):
        """测试Beta系数计算"""
        tool = CalculateBetaTool()
        fund_values = [1.0 + 0.01 * i + 0.005 * np.sin(i) for i in range(50)]
        benchmark_values = [1.0 + 0.008 * i + 0.003 * np.sin(i) for i in range(50)]
        
        result = await tool.execute(
            fund_nav_values=fund_values,
            benchmark_nav_values=benchmark_values
        )
        
        assert result.success is True
        assert "beta" in result.data
        assert "correlation" in result.data
    
    @pytest.mark.asyncio
    async def test_calculate_beta_high_beta(self):
        """测试高Beta基金"""
        tool = CalculateBetaTool()
        fund_values = [1.0 + 0.02 * i for i in range(50)]
        benchmark_values = [1.0 + 0.01 * i for i in range(50)]
        
        result = await tool.execute(
            fund_nav_values=fund_values,
            benchmark_nav_values=benchmark_values
        )
        
        assert result.success is True
        assert result.data["beta"] > 1
    
    @pytest.mark.asyncio
    async def test_risk_metrics_empty_data(self):
        """测试空数据处理"""
        tool = CalculateVolatilityTool()
        
        result = await tool.execute(nav_values=[])
        
        assert result.success is False
