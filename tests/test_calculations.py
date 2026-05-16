import pytest
import numpy as np
from app.core.calculations import (
    calculate_volatility,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_rsi,
)


class TestVolatilityCalculation:

    def test_volatility_with_normal_returns(self):
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.005, 0.01, -0.015, 0.02])
        result = calculate_volatility(returns)
        expected_std = np.std(returns, ddof=1)
        expected = round(float(expected_std * np.sqrt(252) * 100), 2)
        assert result == expected

    def test_volatility_with_single_return(self):
        returns = np.array([0.01])
        result = calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_with_empty_returns(self):
        returns = np.array([])
        result = calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_with_zero_returns(self):
        returns = np.array([0.0, 0.0, 0.0, 0.0])
        result = calculate_volatility(returns)
        assert result == 0.0

    def test_volatility_result_is_positive(self):
        returns = np.array([0.01, -0.01, 0.02, -0.02])
        result = calculate_volatility(returns)
        assert result >= 0.0


class TestMaxDrawdownCalculation:

    def test_max_drawdown_with_known_values(self):
        values = np.array([1.0, 1.5, 2.0, 1.8, 1.5, 1.7])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd == 25.0
        assert idx == 4

    def test_max_drawdown_no_drawdown(self):
        values = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd == 0.0

    def test_max_drawdown_with_single_value(self):
        values = np.array([1.0])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd == 0.0
        assert idx is None

    def test_max_drawdown_with_empty_values(self):
        values = np.array([])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd == 0.0
        assert idx is None

    def test_max_drawdown_full_drawdown(self):
        values = np.array([1.0, 2.0, 0.0])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd == 100.0
        assert idx == 2

    def test_max_drawdown_result_is_non_negative(self):
        values = np.array([1.0, 0.8, 1.2, 0.9, 1.5])
        max_dd, idx = calculate_max_drawdown(values)
        assert max_dd >= 0.0


class TestSharpeRatioCalculation:

    def test_sharpe_ratio_with_positive_returns(self):
        returns = np.array([0.001] * 100)
        result = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert result > 0.0

    def test_sharpe_ratio_with_negative_returns(self):
        returns = np.array([-0.002] * 100)
        result = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert result < 0.0

    def test_sharpe_ratio_with_insufficient_data(self):
        returns = np.array([0.01])
        result = calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_empty_returns(self):
        returns = np.array([])
        result = calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_zero_std(self):
        returns = np.array([0.001, 0.001, 0.001, 0.001])
        result = calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sharpe_ratio_with_known_values(self):
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.015, -0.005, 0.01, -0.01, 0.005, 0.02])
        result = calculate_sharpe_ratio(returns, risk_free_rate=0.0)
        expected_mean = np.mean(returns)
        expected_std = np.std(returns, ddof=1)
        expected_sharpe = round(float(expected_mean / expected_std * np.sqrt(252)), 2)
        assert result == expected_sharpe


class TestSortinoRatioCalculation:

    def test_sortino_ratio_with_mixed_returns(self):
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.005, 0.01, -0.015, 0.02])
        result = calculate_sortino_ratio(returns)
        assert result is not None
        assert isinstance(result, float)

    def test_sortino_ratio_returns_none_when_no_downside(self):
        returns = np.array([0.01, 0.02, 0.015, 0.005, 0.01, 0.02, 0.005, 0.01, 0.015, 0.02])
        result = calculate_sortino_ratio(returns, risk_free_rate=0.02)
        assert result is None

    def test_sortino_ratio_with_insufficient_data(self):
        returns = np.array([0.01])
        result = calculate_sortino_ratio(returns)
        assert result == 0.0

    def test_sortino_ratio_with_empty_returns(self):
        returns = np.array([])
        result = calculate_sortino_ratio(returns)
        assert result == 0.0

    def test_sortino_ratio_with_all_negative_returns(self):
        returns = np.array([-0.01, -0.02, -0.015, -0.005, -0.01, -0.02, -0.005, -0.01, -0.015, -0.02])
        result = calculate_sortino_ratio(returns)
        assert result is not None
        assert result < 0.0


class TestRSICalculation:

    def test_rsi_with_known_values(self):
        values = [100.0]
        for i in range(20):
            if i % 2 == 0:
                values.append(values[-1] * 1.01)
            else:
                values.append(values[-1] * 0.99)
        result = calculate_rsi(values, period=14)
        assert result is not None
        assert 40.0 <= result <= 60.0

    def test_rsi_all_gains(self):
        values = [100.0 + i for i in range(20)]
        result = calculate_rsi(values, period=14)
        assert result == 100.0

    def test_rsi_insufficient_data(self):
        values = [1.0, 2.0, 3.0]
        result = calculate_rsi(values, period=14)
        assert result is None

    def test_rsi_all_losses(self):
        values = [100.0 - i for i in range(20)]
        result = calculate_rsi(values, period=14)
        assert result == 0.0

    def test_rsi_range_is_valid(self):
        values = [1.0, 1.02, 0.99, 1.03, 0.98, 1.01, 1.04, 0.97, 1.02, 0.99,
                  1.05, 0.96, 1.03, 0.98, 1.01, 1.02, 0.99, 1.04, 0.97, 1.02]
        result = calculate_rsi(values, period=14)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_rsi_with_default_period(self):
        values = [100.0]
        for i in range(30):
            values.append(values[-1] * (1 + 0.001 * ((-1) ** i)))
        result = calculate_rsi(values)
        assert result is not None
        assert isinstance(result, float)
