from typing import Dict, Any, Optional, List
import numpy as np


def calculate_scenario_analysis(
    nav_values: List[float]
) -> Dict[str, Any]:
    if not nav_values or len(nav_values) < 60:
        return {
            "error": "净值数据不足，至少需要60个数据点",
            "data_sufficient": False
        }

    arr = np.array(nav_values, dtype=float)
    arr = arr[arr > 0]

    if len(arr) < 60:
        return {
            "error": "有效净值数据不足",
            "data_sufficient": False
        }

    returns = np.diff(arr) / arr[:-1]

    bull_scenario = _analyze_scenario(returns, "bull", 0.001, 0.008)
    bear_scenario = _analyze_scenario(returns, "bear", -0.003, 0.015)
    sideways_scenario = _analyze_scenario(returns, "sideways", 0.0, 0.006)

    current_regime = _detect_current_regime(returns)

    return {
        "bull_market": bull_scenario,
        "bear_market": bear_scenario,
        "sideways_market": sideways_scenario,
        "current_regime": current_regime,
        "data_sufficient": True
    }


def _analyze_scenario(
    returns: np.ndarray,
    regime: str,
    target_mean: float,
    target_std: float
) -> Dict[str, Any]:
    if len(returns) < 30:
        return {"description": "数据不足"}

    window = min(60, len(returns))
    rolling_means = []
    rolling_stds = []

    for i in range(window, len(returns) + 1):
        chunk = returns[i - window:i]
        rolling_means.append(float(np.mean(chunk)))
        rolling_stds.append(float(np.std(chunk, ddof=1)))

    if not rolling_means:
        return {"description": "数据不足"}

    rolling_means = np.array(rolling_means)
    rolling_stds = np.array(rolling_stds)

    if regime == "bull":
        mask = rolling_means > 0
        if not np.any(mask):
            return {
                "avg_daily_return": None,
                "avg_annualized_return": None,
                "avg_volatility": None,
                "frequency": 0.0,
                "description": "历史数据中未出现牛市行情"
            }
        selected_means = rolling_means[mask]
        selected_stds = rolling_stds[mask]
    elif regime == "bear":
        mask = rolling_means < 0
        if not np.any(mask):
            return {
                "avg_daily_return": None,
                "avg_annualized_return": None,
                "avg_volatility": None,
                "frequency": 0.0,
                "description": "历史数据中未出现熊市行情"
            }
        selected_means = rolling_means[mask]
        selected_stds = rolling_stds[mask]
    else:
        mask = (rolling_means >= -0.001) & (rolling_means <= 0.001)
        if not np.any(mask):
            selected_means = rolling_means
            selected_stds = rolling_stds
        else:
            selected_means = rolling_means[mask]
            selected_stds = rolling_stds[mask]

    avg_daily = float(np.mean(selected_means))
    avg_std = float(np.mean(selected_stds))
    frequency = float(np.sum(mask)) / len(rolling_means) if len(rolling_means) > 0 else 0

    return {
        "avg_daily_return": round(avg_daily * 100, 4),
        "avg_annualized_return": round(avg_daily * 252 * 100, 2),
        "avg_volatility": round(avg_std * np.sqrt(252) * 100, 2),
        "frequency": round(frequency * 100, 1),
        "description": _describe_scenario(regime, avg_daily, avg_std, frequency)
    }


def _detect_current_regime(returns: np.ndarray) -> Dict[str, Any]:
    if len(returns) < 20:
        return {"regime": "未知", "confidence": 0}

    recent = returns[-20:]
    recent_mean = float(np.mean(recent))
    recent_std = float(np.std(recent, ddof=1))

    if recent_mean > 0.002:
        regime = "牛市"
        confidence = min(95, int(50 + recent_mean * 10000))
    elif recent_mean < -0.002:
        regime = "熊市"
        confidence = min(95, int(50 + abs(recent_mean) * 10000))
    else:
        regime = "震荡市"
        confidence = min(95, int(50 + (1 - abs(recent_mean) * 1000) * 30))

    return {
        "regime": regime,
        "confidence": confidence,
        "recent_daily_return": round(recent_mean * 100, 4),
        "recent_volatility": round(recent_std * np.sqrt(252) * 100, 2)
    }


def _describe_scenario(regime: str, avg_daily: float, avg_std: float, frequency: float) -> str:
    if regime == "bull":
        return f"牛市行情下日均收益{avg_daily * 100:.3f}%，年化约{avg_daily * 252 * 100:.1f}%，历史出现频率{frequency * 100:.1f}%"
    elif regime == "bear":
        return f"熊市行情下日均亏损{abs(avg_daily) * 100:.3f}%，年化约{avg_daily * 252 * 100:.1f}%，历史出现频率{frequency * 100:.1f}%"
    else:
        return f"震荡行情下日均收益{avg_daily * 100:.3f}%，波动率{avg_std * np.sqrt(252) * 100:.1f}%，历史出现频率{frequency * 100:.1f}%"
