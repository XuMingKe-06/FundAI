from typing import Dict, Any, Optional, List
import numpy as np


def calculate_dca_analysis(
    nav_values: List[float],
    investment_amount: float = 1000.0,
    frequency_days: int = 7
) -> Dict[str, Any]:
    if not nav_values or len(nav_values) < 10:
        return {
            "error": "净值数据不足，至少需要10个数据点",
            "data_sufficient": False
        }

    arr = np.array(nav_values, dtype=float)
    arr = arr[arr > 0]

    if len(arr) < 10:
        return {
            "error": "有效净值数据不足",
            "data_sufficient": False
        }

    dca_result = _simulate_dca(arr, investment_amount, frequency_days)
    lump_sum_result = _simulate_lump_sum(arr, investment_amount, frequency_days)

    total_invested = dca_result["total_invested"]
    dca_final_value = dca_result["final_value"]
    dca_return_rate = (dca_final_value - total_invested) / total_invested if total_invested > 0 else 0

    lump_sum_invested = lump_sum_result["total_invested"]
    lump_sum_final_value = lump_sum_result["final_value"]
    lump_sum_return_rate = (lump_sum_final_value - lump_sum_invested) / lump_sum_invested if lump_sum_invested > 0 else 0

    avg_cost_dca = dca_result["avg_cost"]
    avg_cost_lump = lump_sum_result["avg_cost"]

    if dca_return_rate > lump_sum_return_rate:
        better_strategy = "定投"
        advantage = round((dca_return_rate - lump_sum_return_rate) * 100, 2)
    elif lump_sum_return_rate > dca_return_rate:
        better_strategy = "一次性投入"
        advantage = round((lump_sum_return_rate - dca_return_rate) * 100, 2)
    else:
        better_strategy = "相当"
        advantage = 0.0

    smile_curve = _analyze_smile_curve(arr, frequency_days)

    return {
        "dca": {
            "total_invested": round(total_invested, 2),
            "final_value": round(dca_final_value, 2),
            "return_rate": round(dca_return_rate * 100, 2),
            "avg_cost": round(avg_cost_dca, 4),
            "investment_count": dca_result["investment_count"]
        },
        "lump_sum": {
            "total_invested": round(lump_sum_invested, 2),
            "final_value": round(lump_sum_final_value, 2),
            "return_rate": round(lump_sum_return_rate * 100, 2),
            "avg_cost": round(avg_cost_lump, 4)
        },
        "comparison": {
            "better_strategy": better_strategy,
            "advantage_pct": advantage,
            "dca_lower_cost": avg_cost_dca < avg_cost_lump if avg_cost_lump > 0 else True
        },
        "smile_curve": smile_curve,
        "data_sufficient": True
    }


def _simulate_dca(
    nav_values: np.ndarray,
    investment_amount: float,
    frequency_days: int
) -> Dict[str, Any]:
    total_shares = 0.0
    total_invested = 0.0
    investment_count = 0

    step = max(1, frequency_days)
    indices = list(range(0, len(nav_values), step))

    for idx in indices:
        nav = float(nav_values[idx])
        if nav > 0:
            shares = investment_amount / nav
            total_shares += shares
            total_invested += investment_amount
            investment_count += 1

    final_value = total_shares * float(nav_values[-1]) if total_shares > 0 else 0
    avg_cost = total_invested / total_shares if total_shares > 0 else 0

    return {
        "total_invested": total_invested,
        "final_value": final_value,
        "total_shares": total_shares,
        "avg_cost": avg_cost,
        "investment_count": investment_count
    }


def _simulate_lump_sum(
    nav_values: np.ndarray,
    investment_amount: float,
    frequency_days: int
) -> Dict[str, Any]:
    step = max(1, frequency_days)
    indices = list(range(0, len(nav_values), step))
    total_invested = investment_amount * len(indices)
    total_shares = 0.0

    for idx in indices:
        nav = float(nav_values[idx])
        if nav > 0:
            total_shares += investment_amount / nav

    final_value = total_shares * float(nav_values[-1]) if total_shares > 0 else 0
    avg_cost = total_invested / total_shares if total_shares > 0 else 0

    return {
        "total_invested": total_invested,
        "final_value": final_value,
        "total_shares": total_shares,
        "avg_cost": avg_cost
    }


def _analyze_smile_curve(
    nav_values: np.ndarray,
    frequency_days: int
) -> Dict[str, Any]:
    if len(nav_values) < 30:
        return {"detected": False, "description": "数据不足"}

    returns = np.diff(nav_values) / nav_values[:-1]

    window = min(20, len(returns) // 3)
    if window < 5:
        return {"detected": False, "description": "数据不足"}

    rolling_returns = np.convolve(returns, np.ones(window) / window, mode='valid')

    if len(rolling_returns) < 3:
        return {"detected": False, "description": "数据不足"}

    min_idx = int(np.argmin(rolling_returns))
    first_third = len(rolling_returns) // 3
    last_third = 2 * len(rolling_returns) // 3

    if min_idx > first_third and min_idx < last_third:
        return {
            "detected": True,
            "description": "检测到微笑曲线形态，定投策略在下跌中积累更多份额，反弹后收益更优",
            "low_point_index": min_idx
        }

    return {"detected": False, "description": "未检测到明显微笑曲线形态"}
