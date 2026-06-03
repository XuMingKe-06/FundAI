from typing import Tuple, Optional
import numpy as np

def calculate_max_drawdown(values: np.ndarray) -> Tuple[float, Optional[int]]:
    if len(values) < 2:
        return 0.0, None
    cumulative_max = np.maximum.accumulate(values)
    drawdowns = (cumulative_max - values) / cumulative_max * 100
    max_drawdown = np.max(drawdowns)
    max_drawdown_idx = np.argmax(drawdowns)
    return round(float(max_drawdown), 2), int(max_drawdown_idx)

def calculate_current_drawdown(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    cumulative_max = np.maximum.accumulate(values)
    current_value = values[-1]
    current_max = cumulative_max[-1]
    if current_max == 0:
        return 0.0
    current_drawdown = (current_max - current_value) / current_max * 100
    return round(float(current_drawdown), 2)
