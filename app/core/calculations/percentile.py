from typing import List

def calculate_percentile(current_value: float, historical_values: List[float]) -> float:
    if not historical_values:
        return 50.0
    count_below = sum(1 for v in historical_values if v < current_value)
    percentile = (count_below / len(historical_values)) * 100
    return round(percentile, 1)
