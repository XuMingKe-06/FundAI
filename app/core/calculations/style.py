from typing import Dict, Any, Optional, List
import numpy as np


def calculate_style_box(
    holdings: Optional[Dict[str, Any]],
    nav_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    if not holdings:
        return {
            "market_cap_style": "未知",
            "value_style": "未知",
            "style_box_position": "未知",
            "data_sufficient": False
        }

    stock_list = holdings.get("stock_list", [])
    if not stock_list or len(stock_list) == 0:
        return {
            "market_cap_style": "未知",
            "value_style": "未知",
            "style_box_position": "未知",
            "data_sufficient": False
        }

    market_cap_style = _determine_market_cap_style(stock_list)
    value_style = _determine_value_style(stock_list)
    style_box_position = f"{market_cap_style}-{value_style}"

    top_stocks = stock_list[:10]
    stock_details = []
    for s in top_stocks:
        stock_details.append({
            "name": s.get("stock_name", s.get("name", "未知")),
            "proportion": float(s.get("proportion", 0)),
            "market_cap_level": _classify_single_market_cap(s),
            "value_level": _classify_single_value(s)
        })

    return {
        "market_cap_style": market_cap_style,
        "value_style": value_style,
        "style_box_position": style_box_position,
        "top_stocks_style": stock_details,
        "data_sufficient": True
    }


def _determine_market_cap_style(stock_list: List[Dict[str, Any]]) -> str:
    large_cap_weight = 0.0
    mid_cap_weight = 0.0
    small_cap_weight = 0.0
    total_weight = 0.0

    for stock in stock_list:
        proportion = float(stock.get("proportion", 0))
        if proportion <= 0:
            continue
        total_weight += proportion
        cap_level = _classify_single_market_cap(stock)
        if cap_level == "大盘":
            large_cap_weight += proportion
        elif cap_level == "中盘":
            mid_cap_weight += proportion
        else:
            small_cap_weight += proportion

    if total_weight == 0:
        return "中盘"

    large_pct = large_cap_weight / total_weight
    mid_pct = mid_cap_weight / total_weight
    small_pct = small_cap_weight / total_weight

    if large_pct >= 0.5:
        return "大盘"
    elif small_pct >= 0.5:
        return "小盘"
    elif large_pct >= mid_pct and large_pct >= small_pct:
        return "大盘"
    elif small_pct >= mid_pct and small_pct >= large_pct:
        return "小盘"
    else:
        return "中盘"


def _determine_value_style(stock_list: List[Dict[str, Any]]) -> str:
    value_weight = 0.0
    growth_weight = 0.0
    blend_weight = 0.0
    total_weight = 0.0

    for stock in stock_list:
        proportion = float(stock.get("proportion", 0))
        if proportion <= 0:
            continue
        total_weight += proportion
        value_level = _classify_single_value(stock)
        if value_level == "价值":
            value_weight += proportion
        elif value_level == "成长":
            growth_weight += proportion
        else:
            blend_weight += proportion

    if total_weight == 0:
        return "平衡"

    value_pct = value_weight / total_weight
    growth_pct = growth_weight / total_weight

    if value_pct >= 0.5:
        return "价值"
    elif growth_pct >= 0.5:
        return "成长"
    else:
        return "平衡"


def _classify_single_market_cap(stock: Dict[str, Any]) -> str:
    market_cap = stock.get("market_cap") or stock.get("total_mv")
    if market_cap is not None:
        try:
            cap_val = float(market_cap)
            if cap_val >= 500:
                return "大盘"
            elif cap_val >= 100:
                return "中盘"
            else:
                return "小盘"
        except (ValueError, TypeError):
            pass

    industry = stock.get("industry", "")
    large_cap_industries = ["银行", "保险", "证券", "石油", "电信", "电力", "煤炭", "钢铁", "交通运输"]
    small_cap_industries = ["计算机", "电子", "传媒", "通信", "医药生物", "休闲服务"]

    for ind in large_cap_industries:
        if ind in str(industry):
            return "大盘"
    for ind in small_cap_industries:
        if ind in str(industry):
            return "小盘"

    return "中盘"


def _classify_single_value(stock: Dict[str, Any]) -> str:
    pe = stock.get("pe") or stock.get("pe_ttm")
    pb = stock.get("pb")

    if pe is not None and pb is not None:
        try:
            pe_val = float(pe)
            pb_val = float(pb)
            if pe_val > 0:
                if pe_val <= 15 and pb_val <= 1.5:
                    return "价值"
                elif pe_val > 30 or pb_val > 3:
                    return "成长"
                else:
                    return "平衡"
        except (ValueError, TypeError):
            pass
    elif pe is not None:
        try:
            pe_val = float(pe)
            if pe_val > 0:
                if pe_val <= 15:
                    return "价值"
                elif pe_val > 30:
                    return "成长"
                else:
                    return "平衡"
        except (ValueError, TypeError):
            pass

    industry = stock.get("industry", "")
    value_industries = ["银行", "保险", "证券", "石油", "电力", "煤炭", "钢铁", "房地产", "交通运输"]
    growth_industries = ["计算机", "电子", "传媒", "通信", "医药生物", "新能源", "半导体"]

    for ind in value_industries:
        if ind in str(industry):
            return "价值"
    for ind in growth_industries:
        if ind in str(industry):
            return "成长"

    return "平衡"
