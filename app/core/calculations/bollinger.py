from typing import Dict, Any, Optional, List
import numpy as np


def calculate_bollinger_bands(
    values: List[float],
    period: int = 20,
    num_std: float = 2.0
) -> Dict[str, Any]:
    if not values or len(values) < period:
        return {
            "upper": None,
            "middle": None,
            "lower": None,
            "bandwidth": None,
            "percent_b": None,
            "signal": "数据不足",
            "data_sufficient": False
        }

    arr = np.array(values, dtype=float)
    recent = arr[-period:]

    middle = float(np.mean(recent))
    std = float(np.std(recent, ddof=1))

    upper = middle + num_std * std
    lower = middle - num_std * std

    current = float(arr[-1])

    bandwidth = (upper - lower) / middle if middle > 0 else None

    if upper != lower:
        percent_b = (current - lower) / (upper - lower)
    else:
        percent_b = 0.5

    if current > upper:
        signal = "突破上轨"
    elif current < lower:
        signal = "突破下轨"
    elif percent_b > 0.8:
        signal = "接近上轨"
    elif percent_b < 0.2:
        signal = "接近下轨"
    else:
        signal = "中轨附近"

    return {
        "upper": round(upper, 4),
        "middle": round(middle, 4),
        "lower": round(lower, 4),
        "bandwidth": round(bandwidth, 4) if bandwidth is not None else None,
        "percent_b": round(percent_b, 4),
        "signal": signal,
        "data_sufficient": True
    }
