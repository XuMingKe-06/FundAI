import pytest
import numpy as np
from app.core.calculations import (
    calculate_ma, calculate_ma_slope, calculate_rsi,
    calculate_macd, calculate_volatility,
    calculate_max_drawdown, calculate_current_drawdown,
    calculate_sharpe_ratio, calculate_sortino_ratio,
    calculate_calmar_ratio, calculate_beta,
    calculate_percentile
)
from app.core.calculations.ema import calculate_ema


class TestCalculateMA:
    def test_ma_normal(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert calculate_ma(values, 3) == pytest.approx(4.0)

    def test_ma_insufficient_data(self):
        values = [1.0, 2.0]
        assert calculate_ma(values, 5) is None

    def test_ma_single_period(self):
        values = [3.0]
        assert calculate_ma(values, 1) == pytest.approx(3.0)

    def test_ma_exact_period(self):
        values = [1.0, 2.0, 3.0]
        assert calculate_ma(values, 3) == pytest.approx(2.0)

    @pytest.mark.parametrize("values,period,expected", [
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5, 8.0),
        ([10, 20, 30, 40, 50], 3, 40.0),
        ([1.5, 2.5, 3.5], 2, 3.0),
    ])
    def test_ma_parametrized(self, values, period, expected):
        assert calculate_ma(values, period) == pytest.approx(expected)


class TestCalculateMASlope:
    def test_slope_rising(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        slope = calculate_ma_slope(values, 3)
        assert slope is not None
        assert slope > 0

    def test_slope_insufficient_data(self):
        values = [1.0, 2.0, 3.0]
        assert calculate_ma_slope(values, 3) is None

    def test_slope_exact_minimum(self):
        values = [1.0, 2.0, 3.0, 4.0]
        slope = calculate_ma_slope(values, 3)
        assert slope is not None

    def test_slope_flat(self):
        values = [5.0, 5.0, 5.0, 5.0, 5.0]
        slope = calculate_ma_slope(values, 3)
        assert slope is not None
        assert abs(slope) < 1e-10


class TestCalculateRSI:
    def test_rsi_wilder_vs_sma(self):
        values = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        rsi = calculate_rsi(values, 14)
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert rsi > 50

    def test_rsi_all_gains(self):
        values = list(range(1, 21))
        rsi = calculate_rsi(values, 14)
        assert rsi == 100.0

    def test_rsi_insufficient_data(self):
        values = [1.0, 2.0, 3.0]
        assert calculate_rsi(values, 14) is None

    def test_rsi_mixed_returns(self):
        values = [100, 102, 98, 101, 97, 103, 99, 104, 96, 105,
                  95, 106, 94, 107, 93, 108]
        rsi = calculate_rsi(values, 14)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_rsi_period_7(self):
        values = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42]
        rsi = calculate_rsi(values, 7)
        assert rsi is not None
        assert 0 <= rsi <= 100


class TestCalculateMACD:
    def test_macd_insufficient_data(self):
        values = [1.0, 2.0, 3.0]
        result = calculate_macd(values)
        assert result["macd"] is None

    def test_macd_golden_cross(self):
        values = [100 + i * 0.5 for i in range(50)]
        values[-5:] = [v + 2 for v in values[-5:]]
        result = calculate_macd(values)
        assert result["macd"] is not None
        assert result["signal_type"] in ("金叉", "多头", "空头", "死叉", "震荡")

    def test_macd_death_cross(self):
        values = [100 + i * 0.5 for i in range(50)]
        values[-5:] = [v - 2 for v in values[-5:]]
        result = calculate_macd(values)
        assert result["macd"] is not None


class TestCalculateEMA:
    def test_ema_insufficient_data(self):
        assert calculate_ema([1.0, 2.0], 5) == []

    def test_ema_basic(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        ema = calculate_ema(data, 3)
        assert len(ema) == 3
        assert ema[0] == pytest.approx(2.0)


class TestCalculateVolatility:
    def test_volatility_normal(self):
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
        vol = calculate_volatility(returns)
        assert vol > 0

    def test_volatility_insufficient(self):
        returns = np.array([0.01])
        assert calculate_volatility(returns) == 0.0

    def test_volatility_zero_returns(self):
        returns = np.array([0.0, 0.0, 0.0, 0.0])
        assert calculate_volatility(returns) == 0.0


class TestCalculateDrawdown:
    def test_max_drawdown_normal(self):
        values = np.array([100, 110, 105, 95, 90, 100, 85])
        dd, idx = calculate_max_drawdown(values)
        assert dd > 0
        assert idx is not None

    def test_max_drawdown_no_drawdown(self):
        values = np.array([1, 2, 3, 4, 5])
        dd, idx = calculate_max_drawdown(values)
        assert dd == 0.0

    def test_current_drawdown(self):
        values = np.array([100, 110, 105, 95])
        cd = calculate_current_drawdown(values)
        assert cd > 0

    def test_current_drawdown_at_peak(self):
        values = np.array([100, 110, 120])
        cd = calculate_current_drawdown(values)
        assert cd == 0.0


class TestCalculateRatios:
    def test_sharpe_normal(self):
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.003, 0.008])
        sharpe = calculate_sharpe_ratio(returns)
        assert isinstance(sharpe, float)

    def test_sharpe_insufficient(self):
        returns = np.array([0.01])
        assert calculate_sharpe_ratio(returns) == 0.0

    def test_sortino_no_downside(self):
        returns = np.array([0.01, 0.02, 0.015, 0.005, 0.01])
        sortino = calculate_sortino_ratio(returns)
        assert sortino is None

    def test_sortino_with_downside(self):
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.003, 0.008])
        sortino = calculate_sortino_ratio(returns)
        assert sortino is not None

    def test_calmar_normal(self):
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
        calmar = calculate_calmar_ratio(returns, 5.0)
        assert isinstance(calmar, float)

    def test_calmar_zero_drawdown(self):
        returns = np.array([0.01, 0.02, 0.015])
        assert calculate_calmar_ratio(returns, 0.0) == 0.0

    def test_beta_normal(self):
        fund = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
        bench = np.array([0.008, -0.003, 0.015, -0.008, 0.012])
        beta, corr = calculate_beta(fund, bench)
        assert beta is not None
        assert isinstance(corr, float)

    def test_beta_insufficient_benchmark(self):
        fund = np.array([0.01, 0.02])
        bench = np.array([])
        beta, corr = calculate_beta(fund, bench)
        assert beta is None
        assert corr == 0.0


class TestCalculatePercentile:
    def test_percentile_low(self):
        assert calculate_percentile(1.0, [10, 20, 30, 40, 50]) == 0.0

    def test_percentile_high(self):
        assert calculate_percentile(100.0, [10, 20, 30, 40, 50]) == 100.0

    def test_percentile_middle(self):
        result = calculate_percentile(30.0, [10, 20, 30, 40, 50])
        assert 0 < result < 100

    def test_percentile_empty(self):
        assert calculate_percentile(1.0, []) == 50.0
