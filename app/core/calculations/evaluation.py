from typing import Dict, Any, Optional, List
from loguru import logger

def evaluate_manager_stability(manager_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not manager_info:
        return {
            "stability_score": None,
            "assessment": "无法评估",
            "data_sufficient": False
        }

    name = manager_info.get("name", manager_info.get("fund_manager", "未知"))
    tenure_days = manager_info.get("tenure_days") or manager_info.get("work_duration")
    tenure_years = None
    if tenure_days is not None:
        try:
            tenure_years = round(float(tenure_days) / 365, 1)
        except (ValueError, TypeError):
            pass

    managing_scale = manager_info.get("managing_scale") or manager_info.get("scale")
    managing_fund_count = manager_info.get("managing_fund_count") or manager_info.get("fund_count")

    stability_issues = []
    stability_score = 5.0

    if tenure_years is not None:
        if tenure_years < 1:
            stability_issues.append("任职时间不足1年，经验有限")
            stability_score -= 2.0
        elif tenure_years < 2:
            stability_issues.append("任职时间较短，需关注管理能力")
            stability_score -= 1.0
        elif tenure_years >= 5:
            stability_score += 0.5
    else:
        stability_issues.append("无法获取任职时间信息")
        stability_score -= 1.0

    if managing_fund_count is not None:
        try:
            count = int(managing_fund_count)
            if count > 10:
                stability_issues.append(f"同时管理{count}只基金，精力可能分散")
                stability_score -= 1.0
            elif count > 5:
                stability_score -= 0.5
        except (ValueError, TypeError):
            pass

    if managing_scale is not None:
        try:
            scale = float(managing_scale)
            if scale > 500:
                stability_issues.append(f"管理规模{scale:.0f}亿，规模较大可能影响灵活性")
                stability_score -= 0.5
        except (ValueError, TypeError):
            pass

    stability_score = max(1.0, min(5.0, stability_score))

    if stability_score >= 4:
        assessment = "稳定"
    elif stability_score >= 3:
        assessment = "一般"
    else:
        assessment = "需关注"

    return {
        "manager_name": name,
        "tenure_years": tenure_years,
        "managing_scale": managing_scale,
        "managing_fund_count": managing_fund_count,
        "stability_score": round(stability_score, 1),
        "stability_issues": stability_issues if stability_issues else ["未发现明显稳定性问题"],
        "assessment": assessment,
        "data_sufficient": True
    }

def evaluate_fund_company(fund_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not fund_info:
        return {
            "company_score": None,
            "assessment": "无法评估",
            "data_sufficient": False
        }

    company_name = fund_info.get("management_company") or fund_info.get("fund_company", "未知")
    company_scale = fund_info.get("company_scale") or fund_info.get("management_scale")
    fund_scale = fund_info.get("scale") or fund_info.get("current_scale", 0)
    establish_date = fund_info.get("establish_date")

    company_issues = []
    company_score = 3.0

    if company_scale is not None:
        try:
            scale = float(company_scale)
            if scale > 5000:
                company_score += 1.0
            elif scale > 1000:
                company_score += 0.5
            elif scale < 100:
                company_issues.append("公司管理规模较小，资源可能有限")
                company_score -= 0.5
        except (ValueError, TypeError):
            pass

    if establish_date:
        try:
            from datetime import datetime
            if isinstance(establish_date, str):
                est_date = datetime.strptime(establish_date[:10], "%Y-%m-%d")
            else:
                est_date = establish_date
            from datetime import timezone
            years = (datetime.now(timezone.utc) - est_date).days / 365
            if years < 3:
                company_issues.append("基金成立时间不足3年")
                company_score -= 0.5
            elif years >= 7:
                company_score += 0.5
        except Exception:
            pass

    company_score = max(1.0, min(5.0, company_score))

    if company_score >= 4:
        assessment = "实力较强"
    elif company_score >= 3:
        assessment = "一般"
    else:
        assessment = "实力较弱"

    return {
        "company_name": company_name,
        "company_scale": company_scale,
        "fund_scale": fund_scale,
        "establish_date": establish_date,
        "company_score": round(company_score, 1),
        "company_issues": company_issues if company_issues else ["未发现明显问题"],
        "assessment": assessment,
        "data_sufficient": True
    }
