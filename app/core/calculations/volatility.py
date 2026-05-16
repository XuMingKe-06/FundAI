from typing import Optional
import numpy as np

def calculate_volatility(returns: np.ndarray, annualization_factor: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    std_dev = np.std(returns, ddof=1)
    annual_volatility = std_dev * np.sqrt(annualization_factor) * 100
    return round(float(annual_volatility), 2)
