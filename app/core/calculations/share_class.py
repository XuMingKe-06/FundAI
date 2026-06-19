from typing import Dict, Any, Optional, List
import numpy as np


def calculate_share_class_comparison(
    purchase_fee_a: float,
    purchase_fee_c: float,
    redemption_fee_a: float,
    redemption_fee_c: float,
    sales_service_fee_a: float,
    sales_service_fee_c: float,
    management_fee: float,
    holding_days_list: Optional[List[int]] = None
) -> Dict[str, Any]:
    if holding_days_list is None:
        holding_days_list = [7, 15, 30, 90, 180, 365, 730, 1095]

    results = []
    crossover_day = None

    for days in holding_days_list:
        total_cost_a = _calculate_total_cost(
            purchase_fee_a, redemption_fee_a, sales_service_fee_a,
            management_fee, days
        )
        total_cost_c = _calculate_total_cost(
            purchase_fee_c, redemption_fee_c, sales_service_fee_c,
            management_fee, days
        )

        cheaper = "A类" if total_cost_a < total_cost_c else "C类" if total_cost_c < total_cost_a else "相同"
        cost_diff = abs(total_cost_a - total_cost_c)

        if crossover_day is None and total_cost_c <= total_cost_a:
            crossover_day = days

        results.append({
            "holding_days": days,
            "holding_period": _format_holding_period(days),
            "total_cost_a": round(total_cost_a, 6),
            "total_cost_c": round(total_cost_c, 6),
            "cost_diff": round(cost_diff, 6),
            "cheaper_class": cheaper
        })

    recommendation = _generate_recommendation(crossover_day, results)

    return {
        "comparison": results,
        "crossover_day": crossover_day,
        "recommendation": recommendation,
        "data_sufficient": True
    }


def _calculate_total_cost(
    purchase_fee: float,
    redemption_fee: float,
    sales_service_fee: float,
    management_fee: float,
    holding_days: int
) -> float:
    years = holding_days / 365.0
    total = purchase_fee + redemption_fee + sales_service_fee * years + management_fee * years
    return total


def _format_holding_period(days: int) -> str:
    if days < 30:
        return f"{days}天"
    elif days < 365:
        return f"{days // 30}个月"
    elif days < 730:
        return f"{days // 365}年"
    else:
        return f"{days // 365}年"


def _generate_recommendation(
    crossover_day: Optional[int],
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if crossover_day is None:
        return {
            "short_term": "A类",
            "long_term": "A类",
            "reason": "A类份额在所有持有期内成本均更低"
        }

    if crossover_day <= 30:
        short_term = "C类"
    elif crossover_day <= 180:
        short_term = "视持有期而定"
    else:
        short_term = "A类"

    return {
        "short_term": short_term,
        "long_term": "A类" if crossover_day is not None else "A类",
        "crossover_day": crossover_day,
        "crossover_description": f"持有超过{crossover_day}天后A类份额更优",
        "reason": f"A类份额申购费较高但无销售服务费，C类份额免申购费但有销售服务费，持有{crossover_day}天后A类总成本更低"
    }


def estimate_share_class_fees(
    fees_data: Dict[str, Any]
) -> Dict[str, Any]:
    # 当费率字段值为 None 时（数据源未获取到），使用默认值
    def _safe_float(value, default):
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    purchase_fee = _safe_float(fees_data.get("purchase_fee"), 0.015)
    redemption_fee = _safe_float(fees_data.get("redemption_fee"), 0.005)
    management_fee = _safe_float(fees_data.get("management_fee"), 0.015)
    sales_service_fee_c = _safe_float(fees_data.get("sales_service_fee"), 0.004)

    purchase_fee_a = purchase_fee
    purchase_fee_c = 0.0
    redemption_fee_a = redemption_fee
    redemption_fee_c = redemption_fee
    sales_service_fee_a = 0.0
    sales_service_fee_c = sales_service_fee_c

    return calculate_share_class_comparison(
        purchase_fee_a=purchase_fee_a,
        purchase_fee_c=purchase_fee_c,
        redemption_fee_a=redemption_fee_a,
        redemption_fee_c=redemption_fee_c,
        sales_service_fee_a=sales_service_fee_a,
        sales_service_fee_c=sales_service_fee_c,
        management_fee=management_fee
    )
