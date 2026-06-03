from typing import List

def calculate_ema(data: List[float], period: int) -> List[float]:
    if len(data) < period:
        return []
    ema = []
    multiplier = 2 / (period + 1)
    sma = sum(data[:period]) / period
    ema.append(sma)
    for i in range(period, len(data)):
        ema_value = (data[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(ema_value)
    return ema
