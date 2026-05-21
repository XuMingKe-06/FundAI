from typing import Dict, Any, Optional
from loguru import logger
from app.agents.base import BaseAgent
from app.core.calculations.style import calculate_style_box
from app.core.calculations.evaluation import evaluate_manager_stability, evaluate_fund_company
from app.core.data_provenance import annotate_data_source

class FundamentalAgent(BaseAgent):
    def __init__(self):
        super().__init__("fundamental", "基本面分析师")

    async def _prepare_style_analysis(
        self,
        holdings: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not holdings:
            return {"data_sufficient": False}

        style_result = calculate_style_box(holdings)
        if style_result.get("data_sufficient", False):
            style_result = annotate_data_source(style_result, "style_box")
        return style_result

    async def _prepare_manager_evaluation(
        self,
        manager_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not manager_info:
            return {"data_sufficient": False}

        result = evaluate_manager_stability(manager_info)
        if result.get("data_sufficient", False):
            result = annotate_data_source(result, "manager_evaluation")
        return result

    async def _prepare_company_evaluation(
        self,
        fund_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not fund_info:
            return {"data_sufficient": False}

        result = evaluate_fund_company(fund_info)
        if result.get("data_sufficient", False):
            result = annotate_data_source(result, "company_evaluation")
        return result

    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await self.add_thinking(f"开始对基金 {fund_code} 进行基本面分析...")

        holdings = context.get("holdings", {})
        manager_info = context.get("manager_info", {})
        fund_info = context.get("fund_info", {})

        style_analysis = await self._prepare_style_analysis(holdings)
        if style_analysis.get("data_sufficient", False):
            await self.add_thinking(
                f"风格箱判断: {style_analysis.get('style_box_position', '未知')} "
                f"({style_analysis.get('market_cap_style', '?')}-{style_analysis.get('value_style', '?')})"
            )

        manager_eval = await self._prepare_manager_evaluation(manager_info)
        if manager_eval.get("data_sufficient", False):
            await self.add_thinking(
                f"基金经理稳定性: {manager_eval.get('assessment', '未知')}，"
                f"评分: {manager_eval.get('stability_score', '未知')}"
            )

        company_eval = await self._prepare_company_evaluation(fund_info)
        if company_eval.get("data_sufficient", False):
            await self.add_thinking(
                f"基金公司实力: {company_eval.get('assessment', '未知')}，"
                f"评分: {company_eval.get('company_score', '未知')}"
            )

        enhanced_context = {
            **context,
            "style_analysis": style_analysis,
            "manager_evaluation": manager_eval,
            "company_evaluation": company_eval,
        }

        result = await self.run_llm_analysis(
            fund_code=fund_code,
            context=enhanced_context,
            use_rag=True,
            use_tools=True
        )

        if self.details:
            if style_analysis.get("data_sufficient"):
                self.details["style_box"] = {
                    "market_cap_style": style_analysis.get("market_cap_style"),
                    "value_style": style_analysis.get("value_style"),
                    "style_box_position": style_analysis.get("style_box_position"),
                }
            if manager_eval.get("data_sufficient"):
                self.details["manager_stability"] = {
                    "score": manager_eval.get("stability_score"),
                    "assessment": manager_eval.get("assessment"),
                    "issues": manager_eval.get("stability_issues"),
                }
            if company_eval.get("data_sufficient"):
                self.details["company_strength"] = {
                    "score": company_eval.get("company_score"),
                    "assessment": company_eval.get("assessment"),
                }

        await self.add_thinking(f"基本面分析完成，评分: {self.score}")

        return self.to_dict()
