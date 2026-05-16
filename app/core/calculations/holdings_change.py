from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def analyze_holdings_change(
    current_holdings: Optional[Dict[str, Any]],
    previous_holdings: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if not current_holdings or not previous_holdings:
        return {
            "error": "缺少当前或历史持仓数据",
            "data_sufficient": False
        }

    current_stocks = current_holdings.get("stock_list", [])
    previous_stocks = previous_holdings.get("stock_list", [])

    current_map = {s.get("stock_code", s.get("code", "")): s for s in current_stocks}
    previous_map = {s.get("stock_code", s.get("code", "")): s for s in previous_stocks}

    current_codes = set(current_map.keys())
    previous_codes = set(previous_map.keys())

    new_entries = current_codes - previous_codes
    exited = previous_codes - current_codes
    retained = current_codes & previous_codes

    new_stocks = []
    for code in new_entries:
        stock = current_map[code]
        new_stocks.append({
            "code": code,
            "name": stock.get("stock_name", stock.get("name", "未知")),
            "proportion": float(stock.get("proportion", 0)),
            "action": "新增"
        })

    exited_stocks = []
    for code in exited:
        stock = previous_map[code]
        exited_stocks.append({
            "code": code,
            "name": stock.get("stock_name", stock.get("name", "未知")),
            "previous_proportion": float(stock.get("proportion", 0)),
            "action": "退出"
        })

    adjusted_stocks = []
    for code in retained:
        curr = current_map[code]
        prev = previous_map[code]
        curr_prop = float(curr.get("proportion", 0))
        prev_prop = float(prev.get("proportion", 0))
        change = curr_prop - prev_prop

        if abs(change) > 0.1:
            direction = "增持" if change > 0 else "减持"
            adjusted_stocks.append({
                "code": code,
                "name": curr.get("stock_name", curr.get("name", "未知")),
                "current_proportion": curr_prop,
                "previous_proportion": prev_prop,
                "change": round(change, 2),
                "direction": direction
            })

    adjusted_stocks.sort(key=lambda x: abs(x["change"]), reverse=True)

    current_industries = current_holdings.get("industry_list", [])
    previous_industries = previous_holdings.get("industry_list", [])

    industry_changes = _analyze_industry_changes(current_industries, previous_industries)

    turnover_rate = _estimate_turnover_rate(new_entries, exited, adjusted_stocks, current_stocks)

    current_report_date = current_holdings.get("report_date", "未知")
    previous_report_date = previous_holdings.get("report_date", "未知")

    return {
        "current_report_date": current_report_date,
        "previous_report_date": previous_report_date,
        "new_stocks": new_stocks,
        "exited_stocks": exited_stocks,
        "adjusted_stocks": adjusted_stocks[:10],
        "industry_changes": industry_changes,
        "turnover_rate": turnover_rate,
        "summary": {
            "new_count": len(new_stocks),
            "exited_count": len(exited_stocks),
            "adjusted_count": len(adjusted_stocks),
            "retained_count": len(retained)
        },
        "data_sufficient": True
    }


def _analyze_industry_changes(
    current_industries: List[Dict[str, Any]],
    previous_industries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    current_map = {i.get("industry_name", i.get("industry", "")): i for i in current_industries}
    previous_map = {i.get("industry_name", i.get("industry", "")): i for i in previous_industries}

    all_industries = set(current_map.keys()) | set(previous_map.keys())
    changes = []

    for industry in all_industries:
        curr_prop = float(current_map.get(industry, {}).get("proportion", 0))
        prev_prop = float(previous_map.get(industry, {}).get("proportion", 0))
        change = curr_prop - prev_prop

        if abs(change) >= 0.5:
            direction = "增持" if change > 0 else "减持"
            changes.append({
                "industry": industry,
                "current_proportion": round(curr_prop, 2),
                "previous_proportion": round(prev_prop, 2),
                "change": round(change, 2),
                "direction": direction
            })

    changes.sort(key=lambda x: abs(x["change"]), reverse=True)
    return changes[:10]


def _estimate_turnover_rate(
    new_entries: set,
    exited: set,
    adjusted: List[Dict[str, Any]],
    current_stocks: List[Dict[str, Any]]
) -> Optional[float]:
    if not current_stocks:
        return None

    total_change = len(new_entries) + len(exited)
    for adj in adjusted:
        total_change += abs(adj.get("change", 0))

    total_current = sum(float(s.get("proportion", 0)) for s in current_stocks)
    if total_current == 0:
        return None

    rate = min(total_change / total_current * 100, 200)
    return round(rate, 2)
