from typing import Tuple, Optional
import numpy as np

def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.02,
    annualization_factor: int = 252
) -> float:
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / annualization_factor
    excess_returns = returns - daily_rf
    mean_excess = np.mean(excess_returns)
    std_returns = np.std(returns, ddof=1)
    if std_returns == 0:
        return 0.0
    sharpe = mean_excess / std_returns * np.sqrt(annualization_factor)
    return round(float(sharpe), 2)

def calculate_sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.02,
    annualization_factor: int = 252
) -> Optional[float]:
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / annualization_factor
    excess_returns = returns - daily_rf
    negative_returns = returns[returns < daily_rf]
    if len(negative_returns) == 0:
        return None
    downside_std = np.std(negative_returns, ddof=1)
    if downside_std == 0:
        return 0.0
    sortino = np.mean(excess_returns) / downside_std * np.sqrt(annualization_factor)
    return round(float(sortino), 2)

def calculate_calmar_ratio(
    returns: np.ndarray,
    max_drawdown: float,
    annualization_factor: int = 252
) -> float:
    if len(returns) < 2 or max_drawdown <= 0:
        return 0.0
    annual_return = np.mean(returns) * annualization_factor * 100
    calmar = annual_return / max_drawdown
    return round(float(calmar), 2)

def calculate_beta(
    fund_returns: np.ndarray,
    benchmark_returns: np.ndarray
) -> Tuple[Optional[float], float]:
    if len(fund_returns) < 2 or len(benchmark_returns) < 2:
        return None, 0.0
    min_len = min(len(fund_returns), len(benchmark_returns))
    fund_returns = fund_returns[:min_len]
    benchmark_returns = benchmark_returns[:min_len]
    try:
        covariance = np.cov(fund_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)
        if benchmark_variance == 0:
            return None, 0.0
        beta = covariance / benchmark_variance
        fund_std = np.std(fund_returns, ddof=1)
        benchmark_std = np.std(benchmark_returns, ddof=1)
        if fund_std == 0 or benchmark_std == 0:
            correlation = 0.0
        else:
            correlation = covariance / (fund_std * benchmark_std)
        return round(float(beta), 2), round(float(correlation), 2)
    except Exception:
        return None, 0.0
