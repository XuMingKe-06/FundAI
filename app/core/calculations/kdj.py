from typing import Dict, Any, Optional, List
import numpy as np


def calculate_kdj(
    high_values: List[float],
    low_values: List[float],
    close_values: List[float],
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> Dict[str, Any]:
    if not close_values or len(close_values) < n:
        return {
            "k": None,
            "d": None,
            "j": None,
            "signal": "数据不足",
            "data_sufficient": False
        }

    if not high_values or not low_values:
        close_arr = np.array(close_values, dtype=float)
        high_arr = close_arr.copy()
        low_arr = close_arr.copy()
    else:
        close_arr = np.array(close_values, dtype=float)
        high_arr = np.array(high_values, dtype=float)
        low_arr = np.array(low_values, dtype=float)

    k_values = []
    d_values = []

    prev_k = 50.0
    prev_d = 50.0

    for i in range(n - 1, len(close_arr)):
        period_high = float(np.max(high_arr[i - n + 1:i + 1]))
        period_low = float(np.min(low_arr[i - n + 1:i + 1]))

        if period_high == period_low:
            rsv = 50.0
        else:
            rsv = (close_arr[i] - period_low) / (period_high - period_low) * 100

        k = (2 / m1) * prev_k + (1 / m1) * rsv
        d = (2 / m2) * prev_d + (1 / m2) * k
        j = 3 * k - 2 * d

        k_values.append(float(k))
        d_values.append(float(d))
        prev_k = float(k)
        prev_d = float(d)

    if not k_values:
        return {
            "k": None,
            "d": None,
            "j": None,
            "signal": "数据不足",
            "data_sufficient": False
        }

    current_k = k_values[-1]
    current_d = d_values[-1]
    current_j = 3 * current_k - 2 * current_d

    if current_j > 100:
        signal = "超买"
    elif current_j < 0:
        signal = "超卖"
    elif current_k > current_d and current_k < 80:
        signal = "金叉"
    elif current_k < current_d and current_k > 20:
        signal = "死叉"
    elif current_k > 80:
        signal = "超买区间"
    elif current_k < 20:
        signal = "超卖区间"
    else:
        signal = "震荡"

    return {
        "k": round(current_k, 2),
        "d": round(current_d, 2),
        "j": round(current_j, 2),
        "signal": signal,
        "data_sufficient": True
    }


def calculate_kdj_from_nav(
    nav_values: List[float],
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> Dict[str, Any]:
    if not nav_values or len(nav_values) < n:
        return {
            "k": None,
            "d": None,
            "j": None,
            "signal": "数据不足",
            "data_sufficient": False
        }

    nav_arr = np.array(nav_values, dtype=float)

    if len(nav_arr) < 2:
        return {
            "k": None,
            "d": None,
            "j": None,
            "signal": "数据不足",
            "data_sufficient": False
        }

    returns = np.diff(nav_arr) / nav_arr[:-1]

    high_arr = np.maximum(returns, 0) + 1
    low_arr = np.minimum(returns, 0) + 1
    close_arr = 1 + returns

    high_cum = np.cumprod(high_arr)
    low_cum = np.cumprod(low_arr)
    close_cum = np.cumprod(close_arr)

    return calculate_kdj(
        high_values=high_cum.tolist(),
        low_values=low_cum.tolist(),
        close_values=close_cum.tolist(),
        n=n, m1=m1, m2=m2
    )
