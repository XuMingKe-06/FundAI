"""
计算函数单元测试

测试 RiskAgent 和 TechnicalAgent 中的核心计算方法，
使用已知输入和预期输出验证计算正确性
"""
import pytest
import numpy as np
from app.agents.risk import RiskAgent
from app.agents.technical import TechnicalAgent


class TestVolatilityCalculation:
    """年化波动率计算测试"""

    def setup_method(self):
        self.agent = RiskAgent()

    def test_volatility_with_normal_returns(self):
        """测试正常收益率序列的波动率计算"""
        # 构造标准差已知的收益率序列
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.005, 0.01, -0.015, 0.02])
        result = self.agent._calculate_volatility(returns)

        # 手动计算验证: std(ddof=1) * sqrt(252) * 100
        expected_std = np.std(returns, ddof=1)
        expected = round(float(expected_std * np.sqrt(252) * 100), 2)
        assert result == expected

    def test_volatility_with_single_return(self):
        """测试单条收益率数据返回0"""
        returns = np.array([0.01])
        result = self.agent._calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_with_empty_returns(self):
        """测试空收益率数组返回0"""
        returns = np.array([])
        result = self.agent._calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_with_zero_returns(self):
        """测试全零收益率序列"""
        returns = np.array([0.0, 0.0, 0.0, 0.0])
        result = self.agent._calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_result_is_positive(self):
        """测试波动率结果为非负数"""
        returns = np.array([0.01, -0.01, 0.02, -0.02])
        result = self.agent._calculate_volatility(returns)
        assert result >= 0.0


class TestMaxDrawdownCalculation:
    """最大回撤计算测试"""

    def setup_method(self):
        self.agent = RiskAgent()

    def test_max_drawdown_with_known_values(self):
        """测试已知净值序列的最大回撤计算"""
        # 构造一个明确的回撤场景: 净值先涨到2.0再跌到1.5
        # 最大回撤 = (2.0 - 1.5) / 2.0 * 100 = 25%
        values = np.array([1.0, 1.5, 2.0, 1.8, 1.5, 1.7])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd == 25.0
        # 最大回撤发生在索引4（值1.5，峰值2.0在索引2）
        assert idx == 4

    def test_max_drawdown_no_drawdown(self):
        """测试持续上涨无回撤"""
        values = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd == 0.0

    def test_max_drawdown_with_single_value(self):
        """测试单值序列返回0"""
        values = np.array([1.0])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd == 0.0
        assert idx is None

    def test_max_drawdown_with_empty_values(self):
        """测试空序列返回0"""
        values = np.array([])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd == 0.0
        assert idx is None

    def test_max_drawdown_full_drawdown(self):
        """测试从最高点跌到0的极端情况"""
        values = np.array([1.0, 2.0, 0.0])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd == 100.0
        assert idx == 2

    def test_max_drawdown_result_is_non_negative(self):
        """测试最大回撤结果为非负数"""
        values = np.array([1.0, 0.8, 1.2, 0.9, 1.5])
        max_dd, idx = self.agent._calculate_max_drawdown(values)
        assert max_dd >= 0.0


class TestSharpeRatioCalculation:
    """夏普比率计算测试"""

    def setup_method(self):
        self.agent = RiskAgent()

    def test_sharpe_ratio_with_positive_returns(self):
        """测试正收益序列的夏普比率"""
        # 构造稳定正收益
        returns = np.array([0.001] * 100)
        result = self.agent._calculate_sharpe_ratio(returns, risk_free_rate=0.02)

        # 日均收益0.001，年化约25.2%，远高于2%无风险利率，夏普应为正
        assert result > 0.0

    def test_sharpe_ratio_with_negative_returns(self):
        """测试负收益序列的夏普比率"""
        # 构造稳定负收益
        returns = np.array([-0.002] * 100)
        result = self.agent._calculate_sharpe_ratio(returns, risk_free_rate=0.02)

        # 日均亏损0.002，远低于无风险利率，夏普应为负
        assert result < 0.0

    def test_sharpe_ratio_with_insufficient_data(self):
        """测试数据不足时返回0"""
        returns = np.array([0.01])
        result = self.agent._calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_empty_returns(self):
        """测试空收益率数组返回0"""
        returns = np.array([])
        result = self.agent._calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_zero_std(self):
        """测试标准差为0时返回0"""
        returns = np.array([0.001, 0.001, 0.001, 0.001])
        result = self.agent._calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_known_values(self):
        """测试使用已知值手动计算验证"""
        # 构造已知统计特性的收益率序列
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.015, -0.005, 0.01, -0.01, 0.005, 0.02])
        result = self.agent._calculate_sharpe_ratio(returns, risk_free_rate=0.0)

        # 当 risk_free_rate=0 时: sharpe = mean(returns) / std(returns) * sqrt(252)
        expected_mean = np.mean(returns)
        expected_std = np.std(returns, ddof=1)
        expected_sharpe = round(float(expected_mean / expected_std * np.sqrt(252)), 2)
        assert result == expected_sharpe


class TestSortinoRatioCalculation:
    """索提诺比率计算测试"""

    def setup_method(self):
        self.agent = RiskAgent()

    def test_sortino_ratio_with_mixed_returns(self):
        """测试混合正负收益的索提诺比率"""
        # 包含正收益和负收益
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.005, 0.01, -0.015, 0.02])
        result = self.agent._calculate_sortino_ratio(returns)

        # 有下行风险，应返回一个浮点数
        assert result is not None
        assert isinstance(result, float)

    def test_sortino_ratio_returns_none_when_no_downside(self):
        """测试无下行风险时返回None"""
        # 所有收益都高于无风险日利率(0.02/252 ≈ 0.0000794)
        returns = np.array([0.01, 0.02, 0.015, 0.005, 0.01, 0.02, 0.005, 0.01, 0.015, 0.02])
        result = self.agent._calculate_sortino_ratio(returns, risk_free_rate=0.02)

        # 所有收益都高于日无风险利率，无下行风险，应返回None
        assert result is None

    def test_sortino_ratio_with_insufficient_data(self):
        """测试数据不足时返回0"""
        returns = np.array([0.01])
        result = self.agent._calculate_sortino_ratio(returns)
        assert result == 0.0

    def test_sortino_ratio_with_empty_returns(self):
        """测试空收益率数组返回0"""
        returns = np.array([])
        result = self.agent._calculate_sortino_ratio(returns)
        assert result == 0.0

    def test_sortino_ratio_with_all_negative_returns(self):
        """测试全负收益的索提诺比率"""
        returns = np.array([-0.01, -0.02, -0.015, -0.005, -0.01, -0.02, -0.005, -0.01, -0.015, -0.02])
        result = self.agent._calculate_sortino_ratio(returns)

        # 全部亏损，均值低于无风险利率，索提诺应为负
        assert result is not None
        assert result < 0.0


class TestRSICalculation:
    """RSI指标计算测试"""

    def setup_method(self):
        self.agent = TechnicalAgent()

    def test_rsi_with_known_values(self):
        """测试使用已知值验证RSI计算"""
        # 构造14天数据：7天上涨各1%，7天下跌各1%
        # 最近14个变化: 交替涨跌
        values = [100.0]
        for i in range(20):
            if i % 2 == 0:
                values.append(values[-1] * 1.01)
            else:
                values.append(values[-1] * 0.99)

        result = self.agent._calculate_rsi(values, period=14)

        # 交替涨跌，RSI应接近50
        assert result is not None
        assert 40.0 <= result <= 60.0

    def test_rsi_all_gains(self):
        """测试持续上涨时RSI为100"""
        # 持续上涨
        values = [100.0 + i for i in range(20)]
        result = self.agent._calculate_rsi(values, period=14)

        # 所有变化都是正的，RSI应为100
        assert result == 100.0

    def test_rsi_insufficient_data(self):
        """测试数据不足时返回None"""
        # RSI需要 period+1 个数据点
        values = [1.0, 2.0, 3.0]  # 只有3个点，period=14需要15个
        result = self.agent._calculate_rsi(values, period=14)
        assert result is None

    def test_rsi_all_losses(self):
        """测试持续下跌时RSI为0"""
        # 持续下跌
        values = [100.0 - i for i in range(20)]
        result = self.agent._calculate_rsi(values, period=14)

        # 所有变化都是负的，avg_gain=0，RS=0，RSI=0
        assert result == 0.0

    def test_rsi_range_is_valid(self):
        """测试RSI值在0-100范围内"""
        # 构造混合涨跌的数据
        values = [1.0, 1.02, 0.99, 1.03, 0.98, 1.01, 1.04, 0.97, 1.02, 0.99,
                  1.05, 0.96, 1.03, 0.98, 1.01, 1.02, 0.99, 1.04, 0.97, 1.02]
        result = self.agent._calculate_rsi(values, period=14)

        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_rsi_with_default_period(self):
        """测试默认周期14"""
        values = [100.0]
        for i in range(30):
            values.append(values[-1] * (1 + 0.001 * ((-1) ** i)))

        result = self.agent._calculate_rsi(values)
        assert result is not None
        assert isinstance(result, float)
