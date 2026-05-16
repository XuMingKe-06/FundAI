from typing import Dict, Any, Optional, List, Tuple
import numpy as np


def calculate_var(
    returns: np.ndarray,
    confidence_level: float = 0.95,
    method: str = "historical"
) -> Optional[float]:
    if returns is None or len(returns) < 20:
        return None

    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 20:
        return None

    if method == "historical":
        return _var_historical(returns, confidence_level)
    elif method == "parametric":
        return _var_parametric(returns, confidence_level)
    else:
        return _var_historical(returns, confidence_level)


def calculate_cvar(
    returns: np.ndarray,
    confidence_level: float = 0.95
) -> Optional[float]:
    if returns is None or len(returns) < 20:
        return None

    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 20:
        return None

    var = _var_historical(returns, confidence_level)
    if var is None:
        return None

    tail_returns = returns[returns <= var]
    if len(tail_returns) == 0:
        return var

    return float(np.mean(tail_returns))


def calculate_downside_risk(
    returns: np.ndarray,
    threshold: float = 0.0,
    annualization_factor: int = 252
) -> Optional[float]:
    if returns is None or len(returns) < 10:
        return None

    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return None

    downside_returns = returns[returns < threshold] - threshold
    if len(downside_returns) == 0:
        return 0.0

    downside_dev = float(np.std(downside_returns, ddof=1))
    annualized = downside_dev * np.sqrt(annualization_factor) * 100

    return round(annualized, 4)


def stress_test(
    nav_values: np.ndarray,
    scenarios: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    if nav_values is None or len(nav_values) < 30:
        return {"error": "净值数据不足，至少需要30个数据点", "data_sufficient": False}

    nav_values = np.asarray(nav_values, dtype=float)
    nav_values = nav_values[nav_values > 0]

    if len(nav_values) < 30:
        return {"error": "有效净值数据不足", "data_sufficient": False}

    if scenarios is None:
        scenarios = {
            "2015股灾": -0.45,
            "2020疫情": -0.15,
            "2022回调": -0.20,
            "极端下跌": -0.30,
            "温和下跌": -0.10,
        }

    returns = np.diff(nav_values) / nav_values[:-1]

    current_nav = float(nav_values[-1])

    results = {}
    for scenario_name, shock_pct in scenarios.items():
        shocked_nav = current_nav * (1 + shock_pct)
        loss_amount = current_nav - shocked_nav
        loss_pct = abs(shock_pct) * 100

        historical_similar = _find_similar_historical_shock(returns, shock_pct)

        recovery_days = _estimate_recovery_days(returns, shock_pct)

        results[scenario_name] = {
            "shock_pct": shock_pct,
            "shocked_nav": round(shocked_nav, 4),
            "loss_pct": round(loss_pct, 2),
            "loss_amount_per_unit": round(loss_amount, 4),
            "historical_similar": historical_similar,
            "estimated_recovery_days": recovery_days
        }

    var_95 = calculate_var(returns, 0.95)
    var_99 = calculate_var(returns, 0.99)
    cvar_95 = calculate_cvar(returns, 0.95)
    downside = calculate_downside_risk(returns)

    return {
        "scenarios": results,
        "var_95": round(var_95 * 100, 4) if var_95 is not None else None,
        "var_99": round(var_99 * 100, 4) if var_99 is not None else None,
        "cvar_95": round(cvar_95 * 100, 4) if cvar_95 is not None else None,
        "downside_risk": downside,
        "current_nav": round(current_nav, 4),
        "data_sufficient": True
    }


def _var_historical(returns: np.ndarray, confidence_level: float) -> Optional[float]:
    if len(returns) < 20:
        return None
    index = int(np.floor((1 - confidence_level) * len(returns)))
    sorted_returns = np.sort(returns)
    return float(sorted_returns[index])


def _var_parametric(returns: np.ndarray, confidence_level: float) -> Optional[float]:
    if len(returns) < 20:
        return None
    from scipy import stats
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)
    z_score = stats.norm.ppf(1 - confidence_level)
    return float(mean + z_score * std)


def _find_similar_historical_shock(returns: np.ndarray, shock_pct: float) -> Optional[Dict[str, Any]]:
    if len(returns) < 20:
        return None

    rolling_20 = np.lib.stride_tricks.sliding_window_view(returns, 20)
    if len(rolling_20) == 0:
        return None

    cumulative_returns = np.prod(1 + rolling_20, axis=1) - 1

    target = shock_pct
    distances = np.abs(cumulative_returns - target)
    closest_idx = int(np.argmin(distances))

    return {
        "period_return": round(float(cumulative_returns[closest_idx]) * 100, 2),
        "similarity": round(1 - float(distances[closest_idx] / abs(target)), 4) if abs(target) > 0 else 0
    }


def _estimate_recovery_days(returns: np.ndarray, shock_pct: float) -> Optional[int]:
    if len(returns) < 60:
        return None

    mean_daily_return = float(np.mean(returns))
    if mean_daily_return <= 0:
        return None

    recovery_factor = abs(shock_pct) / mean_daily_return
    recovery_days = int(np.ceil(recovery_factor))

    if recovery_days > 252 * 3:
        return None

    return recovery_days
