from typing import List, Optional, Tuple

def calculate_ma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    recent_values = values[-period:]
    return sum(recent_values) / period

def calculate_ma_slope(values: List[float], period: int) -> Optional[float]:
    if len(values) < period + 1:
        return None
    current_ma = sum(values[-period:]) / period
    prev_ma = sum(values[-(period+1):-1]) / period
    return current_ma - prev_ma
