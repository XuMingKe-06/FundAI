from typing import List, Dict, Any, Optional
from app.core.calculations.ema import calculate_ema

def calculate_macd(
    values: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, Any]:
    if len(values) < slow_period:
        return {
            "macd": None, "signal": None,
            "histogram": None, "signal_type": "数据不足"
        }
    
    ema_fast = calculate_ema(values, fast_period)
    ema_slow = calculate_ema(values, slow_period)
    
    offset = len(ema_fast) - len(ema_slow)
    macd_line = []
    for i in range(len(ema_slow)):
        if offset + i < len(ema_fast):
            macd_line.append(ema_fast[offset + i] - ema_slow[i])
    
    if len(macd_line) < signal_period:
        return {
            "macd": None, "signal": None,
            "histogram": None, "signal_type": "数据不足"
        }
    
    signal_line = calculate_ema(macd_line, signal_period)
    
    if not signal_line:
        return {
            "macd": None, "signal": None,
            "histogram": None, "signal_type": "数据不足"
        }
    
    current_macd = macd_line[-1]
    current_signal = signal_line[-1]
    current_histogram = current_macd - current_signal
    
    signal_type = "震荡"
    if len(macd_line) >= 2 and len(signal_line) >= 2:
        prev_macd = macd_line[-2]
        prev_signal = signal_line[-2]
        if prev_macd <= prev_signal and current_macd > current_signal:
            signal_type = "金叉"
        elif prev_macd >= prev_signal and current_macd < current_signal:
            signal_type = "死叉"
        elif current_macd > current_signal:
            signal_type = "多头"
        else:
            signal_type = "空头"
    
    return {
        "macd": round(current_macd, 6),
        "signal": round(current_signal, 6),
        "histogram": round(current_histogram, 6),
        "signal_type": signal_type
    }
