from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date
from loguru import logger

DAILY_RETURN_THRESHOLD = 0.20

class DataQualityReport:
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def add_issue(self, field: str, issue_type: str, message: str, value: Any = None):
        self.issues.append({
            "field": field,
            "type": issue_type,
            "message": message,
            "value": value
        })

    def add_warning(self, field: str, warning_type: str, message: str, value: Any = None):
        self.warnings.append({
            "field": field,
            "type": warning_type,
            "message": message,
            "value": value
        })

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "has_warnings": self.has_warnings,
            "issue_count": len(self.issues),
            "warning_count": len(self.warnings),
            "issues": self.issues,
            "warnings": self.warnings
        }

def validate_nav_history(nav_history: List[Dict[str, Any]]) -> DataQualityReport:
    report = DataQualityReport()
    if not nav_history:
        report.add_issue("nav_history", "empty", "净值历史数据为空")
        return report

    prev_nav = None
    for i, item in enumerate(nav_history):
        nav = item.get("nav") or item.get("unit_nav")
        if nav is None:
            report.add_warning(f"nav_history[{i}]", "missing_value", f"第{i}条记录缺少净值", None)
            continue
        nav = float(nav)
        if nav <= 0:
            report.add_issue(f"nav_history[{i}]", "invalid_value", f"第{i}条净值非正数", nav)
            continue
        if prev_nav is not None and prev_nav > 0:
            daily_return = (nav - prev_nav) / prev_nav
            if abs(daily_return) > DAILY_RETURN_THRESHOLD:
                report.add_warning(
                    f"nav_history[{i}]",
                    "anomalous_return",
                    f"日收益率异常: {daily_return:.2%}",
                    round(daily_return, 4)
                )
        prev_nav = nav

    return report

def validate_fund_info(fund_info: Dict[str, Any]) -> DataQualityReport:
    report = DataQualityReport()
    if not fund_info:
        report.add_issue("fund_info", "empty", "基金基础信息为空")
        return report

    required_fields = ["fund_code", "fund_name"]
    for field in required_fields:
        if not fund_info.get(field):
            report.add_issue(field, "missing", f"缺少必要字段: {field}")

    return report

def validate_holdings(holdings: Dict[str, Any]) -> DataQualityReport:
    report = DataQualityReport()
    if not holdings:
        report.add_issue("holdings", "empty", "持仓数据为空")
        return report

    report_date = holdings.get("report_date")
    if report_date:
        try:
            if isinstance(report_date, str):
                rd = datetime.strptime(report_date, "%Y-%m-%d").date()
            elif isinstance(report_date, date):
                rd = report_date
            else:
                rd = None

            if rd:
                days_lag = (date.today() - rd).days
                if days_lag > 120:
                    report.add_warning(
                        "report_date",
                        "stale_data",
                        f"持仓数据已滞后{days_lag}天，可能已不准确",
                        days_lag
                    )
        except (ValueError, TypeError):
            report.add_warning("report_date", "invalid_format", "报告日期格式异常", report_date)

    stock_list = holdings.get("stock_list", [])
    for i, stock in enumerate(stock_list[:10]):
        proportion = stock.get("proportion")
        if proportion is not None:
            prop = float(proportion)
            if prop < 0 or prop > 100:
                report.add_warning(
                    f"stock_list[{i}].proportion",
                    "out_of_range",
                    f"持仓比例异常: {prop}%",
                    prop
                )

    return report

def validate_fees(fees_data: Dict[str, Any]) -> DataQualityReport:
    report = DataQualityReport()
    if not fees_data:
        report.add_issue("fees", "empty", "费率数据为空")
        return report

    purchase_fee = fees_data.get("purchase_fee")
    if purchase_fee is not None:
        pf = float(purchase_fee)
        if pf < 0 or pf > 0.1:
            report.add_warning("purchase_fee", "out_of_range", f"申购费率异常: {pf}", pf)

    management_fee = fees_data.get("management_fee")
    if management_fee is not None:
        mf = float(management_fee)
        if mf < 0 or mf > 0.05:
            report.add_warning("management_fee", "out_of_range", f"管理费率异常: {mf}", mf)

    return report

def check_data_timeliness(data_date: Optional[str], max_lag_days: int = 90) -> Optional[Dict[str, Any]]:
    if not data_date:
        return {"is_timely": False, "lag_days": None, "message": "无日期信息"}
    try:
        if isinstance(data_date, str):
            d = datetime.strptime(data_date, "%Y-%m-%d").date()
        elif isinstance(data_date, date):
            d = data_date
        else:
            return {"is_timely": False, "lag_days": None, "message": "日期格式异常"}

        lag_days = (date.today() - d).days
        return {
            "is_timely": lag_days <= max_lag_days,
            "lag_days": lag_days,
            "message": f"数据滞后{lag_days}天" if lag_days > max_lag_days else "数据时效性正常"
        }
    except (ValueError, TypeError):
        return {"is_timely": False, "lag_days": None, "message": "日期解析失败"}
