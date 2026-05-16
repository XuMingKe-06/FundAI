from typing import Dict, Any, Optional, List, Tuple
import numpy as np


def calculate_support_resistance(
    nav_values: List[float],
    num_levels: int = 3,
    window: int = 20,
    tolerance: float = 0.02
) -> Dict[str, Any]:
    if not nav_values or len(nav_values) < window * 2:
        return {
            "support_levels": [],
            "resistance_levels": [],
            "current_position": "未知",
            "data_sufficient": False
        }

    arr = np.array(nav_values, dtype=float)
    current_nav = float(arr[-1])

    pivot_highs = []
    pivot_lows = []

    for i in range(window, len(arr) - window):
        local_slice = arr[i - window:i + window + 1]
        if arr[i] == np.max(local_slice):
            pivot_highs.append(float(arr[i]))
        if arr[i] == np.min(local_slice):
            pivot_lows.append(float(arr[i]))

    support_levels = _cluster_levels(pivot_lows, tolerance, num_levels)
    resistance_levels = _cluster_levels(pivot_highs, tolerance, num_levels)

    support_levels = sorted([s for s in support_levels if s < current_nav], reverse=True)[:num_levels]
    resistance_levels = sorted([r for r in resistance_levels if r > current_nav])[:num_levels]

    if not support_levels:
        min_nav = float(np.min(arr))
        if min_nav < current_nav:
            support_levels = [round(min_nav, 4)]

    if not resistance_levels:
        max_nav = float(np.max(arr))
        if max_nav > current_nav:
            resistance_levels = [round(max_nav, 4)]

    nearest_support = support_levels[0] if support_levels else None
    nearest_resistance = resistance_levels[0] if resistance_levels else None

    if nearest_support and nearest_resistance:
        support_dist = (current_nav - nearest_support) / current_nav * 100
        resistance_dist = (nearest_resistance - current_nav) / current_nav * 100
        if support_dist < resistance_dist:
            position = "接近支撑位"
        else:
            position = "接近阻力位"
    elif nearest_support:
        position = "接近支撑位"
    elif nearest_resistance:
        position = "接近阻力位"
    else:
        position = "中间位置"

    return {
        "support_levels": [round(s, 4) for s in support_levels],
        "resistance_levels": [round(r, 4) for r in resistance_levels],
        "current_nav": round(current_nav, 4),
        "nearest_support": round(nearest_support, 4) if nearest_support else None,
        "nearest_resistance": round(nearest_resistance, 4) if nearest_resistance else None,
        "support_distance_pct": round((current_nav - nearest_support) / current_nav * 100, 2) if nearest_support else None,
        "resistance_distance_pct": round((nearest_resistance - current_nav) / current_nav * 100, 2) if nearest_resistance else None,
        "current_position": position,
        "data_sufficient": True
    }


def _cluster_levels(
    levels: List[float],
    tolerance: float,
    max_clusters: int
) -> List[float]:
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        if abs(level - np.mean(current_cluster)) / np.mean(current_cluster) < tolerance:
            current_cluster.append(level)
        else:
            clusters.append(float(np.mean(current_cluster)))
            current_cluster = [level]

    clusters.append(float(np.mean(current_cluster)))

    level_counts = []
    sorted_levels_arr = np.array(sorted_levels)
    for c in clusters:
        count = int(np.sum(np.abs(sorted_levels_arr - c) / c < tolerance))
        level_counts.append((c, count))

    level_counts.sort(key=lambda x: x[1], reverse=True)
    return [round(lc[0], 4) for lc in level_counts[:max_clusters]]
