"""
基本面分析师提示词模板
负责基金经理能力评估、持仓结构分析、业绩表现评价
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates,
    AnalysisDimension
)


class FundamentalPromptTemplate(PromptTemplate):
    """
    基本面分析师提示词模板
    
    分析维度：
    1. 基金经理能力评估
    2. 持仓结构分析
    3. 业绩表现评价
    """
    
    def __init__(self):
        super().__init__(
            agent_type="fundamental",
            agent_name="基本面分析师",
            score_range=(1, 5)
        )
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        role_def = CommonTemplates.get_role_definition_template(
            role_name="基金基本面分析师",
            expertise=[
                "基金经理能力评估与履历分析",
                "基金持仓结构与行业配置研究",
                "基金业绩表现与基准比较分析",
                "基金规模变动与资金流向研究"
            ]
        )
        
        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "基金经理能力评估",
                "description": "分析基金经理从业年限、历史业绩、管理规模、投资风格稳定性等"
            },
            {
                "name": "持仓结构分析",
                "description": "评估前十大持仓占比、行业分布集中度、持仓调整频率等"
            },
            {
                "name": "业绩表现评价",
                "description": "计算累计收益率、超额收益、信息比率、同类排名等指标"
            },
            {
                "name": "综合评分计算",
                "description": "基于权重配置（基金经理30%、持仓结构25%、业绩表现45%）计算综合评分"
            }
        ])
        
        scoring_criteria = CommonTemplates.get_scoring_criteria_template([
            {"range": "5.0分", "description": "基金经理经验丰富（>=10年），持仓结构合理，业绩表现优秀（超额收益>=10%）"},
            {"range": "4.0-4.9分", "description": "基金经理经验充足（>=7年），持仓结构适中，业绩表现良好（超额收益>=5%）"},
            {"range": "3.0-3.9分", "description": "基金经理经验一般（>=3年），持仓结构可接受，业绩表现平稳（超额收益>=0）"},
            {"range": "2.0-2.9分", "description": "基金经理经验较少（<3年），持仓集中度过高或过低，业绩表现一般（超额收益<0）"},
            {"range": "1.0-1.9分", "description": "基金经理经验不足，持仓结构不合理，业绩表现较差（超额收益<-5%）"}
        ])
        
        output_format = self._get_output_format_instruction()
        
        return f"""{role_def}

{analysis_framework}

{scoring_criteria}

{output_format}

## 分析原则

1. **客观性原则**：基于数据事实进行分析，避免主观臆断
2. **全面性原则**：综合考虑各维度因素，不遗漏重要信息
3. **专业性原则**：使用专业术语和分析方法，体现专业水准
4. **实用性原则**：结论应具有实际参考价值，便于投资决策

## 特别说明

- 持仓数据存在披露滞后性，需在分析中说明
- 基金经理变更需特别关注，可能影响投资风格
- 规模过大或过小都可能影响基金运作效率
- 行业集中度需结合市场环境综合评估

## 数据诚实规则
1. 如果提供的数据中包含 '数据不可用'、'暂不支持' 或 ToolResult.fail 的结果，你必须在分析中明确标注该数据不可用
2. 绝对不得在数据不足时编造或推测分析结论
3. 如果关键数据缺失，应降低 confidence 评分并在 summary 中说明
4. 不得将默认值或占位数据当作真实数据进行分析"""
    
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        fund_info = context.get("fund_info", {})
        holdings = context.get("holdings", {})
        manager_info = context.get("manager_info", {})
        performance = context.get("performance", {})
        
        data_context = f"""## 基金基础信息
- 基金代码：{fund_info.get('fund_code', '未知')}
- 基金名称：{fund_info.get('fund_name', '未知')}
- 基金类型：{fund_info.get('fund_type', '未知')}
- 成立日期：{fund_info.get('establish_date', '未知')}
- 基金规模：{fund_info.get('current_scale', '未知')}亿元
- 基金经理：{fund_info.get('fund_manager', '未知')}

## 基金经理信息
- 基金经理姓名：{manager_info.get('name', '未知')}
- 从业年限：{manager_info.get('experience_years', '未知')}年
- 管理本基金起始日期：{manager_info.get('start_date', '未知')}
- 历史年化收益率：{manager_info.get('annual_return', '未知')}%
- 管理基金数量：{manager_info.get('fund_count', '未知')}只
- 管理总规模：{manager_info.get('total_scale', '未知')}亿元

## 持仓结构数据
- 报告期：{holdings.get('report_date', '未知')}
- 前十大持仓占比：{holdings.get('top10_holding_ratio', '未知')}%
- 行业分布：{holdings.get('industry_concentration', '未知')}
- 股票仓位：{holdings.get('stock_position', '未知')}%
- 债券仓位：{holdings.get('bond_position', '未知')}%

前十大重仓股：
{self._format_top_holdings(holdings.get('stock_list', []))}

## 业绩表现数据
- 近1年收益率：{performance.get('return_1y', '未知')}%
- 近3年收益率：{performance.get('return_3y', '未知')}%
- 今年以来收益率：{performance.get('return_ytd', '未知')}%
- 基准收益率（近1年）：{performance.get('benchmark_return_1y', '未知')}%
- 超额收益（近1年）：{performance.get('alpha_1y', '未知')}%
- 信息比率：{performance.get('information_ratio', '未知')}
- 同类排名：{performance.get('rank_percentile', '未知')}%

## 补充信息
{context.get('additional_info', '无')}"""
        
        return f"""请对以上基金进行基本面分析。

{data_context}

请按照分析框架逐步分析，并输出符合格式要求的JSON结果。"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        base_schema = StandardOutputSchema.get_base_schema(1.0, 5.0)
        
        base_schema["properties"]["details"] = {
            "type": "object",
            "required": [
                "fund_manager",
                "management_experience_years",
                "fund_scale",
                "top10_holding_ratio",
                "industry_concentration",
                "alpha_1y",
                "information_ratio",
                "holding_data_date",
                "score_factors"
            ],
            "properties": {
                "fund_manager": {
                    "type": "string",
                    "description": "基金经理姓名"
                },
                "management_experience_years": {
                    "type": "number",
                    "description": "基金经理从业年限"
                },
                "fund_scale": {
                    "type": "number",
                    "description": "基金规模（亿元）"
                },
                "top10_holding_ratio": {
                    "type": "number",
                    "description": "前十大持仓占比（%）"
                },
                "industry_concentration": {
                    "type": "string",
                    "description": "主要行业分布"
                },
                "alpha_1y": {
                    "type": "number",
                    "description": "近1年超额收益率（%）"
                },
                "information_ratio": {
                    "type": "number",
                    "description": "信息比率"
                },
                "holding_data_date": {
                    "type": "string",
                    "description": "持仓数据截止日期"
                },
                "score_factors": {
                    "type": "object",
                    "description": "各维度评分因子",
                    "properties": {
                        "基金经理": {"type": "number"},
                        "持仓结构": {"type": "number"},
                        "业绩表现": {"type": "number"}
                    }
                }
            }
        }
        
        return base_schema
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return CommonTemplates.get_output_format_instruction(schema)
    
    def _format_top_holdings(self, stock_list: list) -> str:
        """格式化前十大持仓"""
        if not stock_list:
            return "暂无持仓数据"
        
        lines = []
        for i, stock in enumerate(stock_list[:10], 1):
            name = stock.get('stock_name', '未知')
            code = stock.get('stock_code', '未知')
            ratio = stock.get('holding_ratio', 0)
            industry = stock.get('industry', '未知')
            lines.append(f"  {i}. {name}({code}) - 持仓比例: {ratio}%, 行业: {industry}")
        
        return "\n".join(lines)


FUNDAMENTAL_SYSTEM_PROMPT = FundamentalPromptTemplate().get_system_prompt()
FUNDAMENTAL_OUTPUT_SCHEMA = FundamentalPromptTemplate().get_output_schema()
