"""
风险分析师提示词模板
负责波动率分析、最大回撤评估、夏普比率计算、风险等级划分
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates
)


class RiskPromptTemplate(PromptTemplate):
    """
    风险分析师提示词模板
    
    分析维度：
    1. 波动率分析
    2. 最大回撤评估
    3. 夏普比率计算
    4. Beta系数分析
    5. 集中度风险分析
    """
    
    def __init__(self):
        super().__init__(
            agent_type="risk",
            agent_name="风险分析师",
            score_range=(1, 5)
        )
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        role_def = CommonTemplates.get_role_definition_template(
            role_name="基金风险评估师",
            expertise=[
                "波动率分析与风险评估",
                "最大回撤计算与下行风险分析",
                "夏普比率、卡玛比率等风险调整收益指标计算",
                "Beta系数与系统性风险分析",
                "持仓集中度风险识别"
            ]
        )
        
        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "波动率分析",
                "description": "计算年化波动率，评估净值波动程度，判断市场风险暴露水平"
            },
            {
                "name": "最大回撤评估",
                "description": "计算历史最大回撤及发生时间，评估下行风险承受能力"
            },
            {
                "name": "夏普比率计算",
                "description": "计算风险调整后收益，评估单位风险获得的超额收益"
            },
            {
                "name": "Beta系数分析",
                "description": "计算相对于基准的Beta系数，评估系统性风险暴露"
            },
            {
                "name": "集中度风险分析",
                "description": "分析前十大持仓占比、单一行业集中度，识别潜在风险点"
            },
            {
                "name": "风险等级评定",
                "description": "综合各风险指标，评定整体风险等级（低/中/高）"
            }
        ])
        
        scoring_criteria = CommonTemplates.get_scoring_criteria_template([
            {"range": "5.0分（低风险）", "description": "年化波动率<10%，最大回撤<10%，夏普比率>1.0，Beta<1，集中度合理"},
            {"range": "4.0-4.9分（低风险）", "description": "年化波动率10%-15%，最大回撤10%-15%，夏普比率0.5-1.0，Beta接近1"},
            {"range": "3.0-3.9分（中风险）", "description": "年化波动率15%-20%，最大回撤15%-20%，夏普比率0-0.5，Beta略高"},
            {"range": "2.0-2.9分（高风险）", "description": "年化波动率20%-25%，最大回撤20%-30%，夏普比率<0，Beta>1.2"},
            {"range": "1.0-1.9分（高风险）", "description": "年化波动率>25%，最大回撤>30%，夏普比率<-0.5，Beta>1.5，集中度极高"}
        ])
        
        output_format = self._get_output_format_instruction()
        
        return f"""{role_def}

{analysis_framework}

{scoring_criteria}

{output_format}

## 风险指标说明

### 年化波动率
- **计算公式**：σ_annual = σ_daily × √252
- **解读**：
  - < 10%：低波动，适合稳健投资者
  - 10%-20%：中等波动，需关注市场变化
  - > 20%：高波动，需谨慎投资

### 最大回撤
- **定义**：历史最高点到最低点的最大跌幅
- **解读**：
  - < 10%：风险控制良好
  - 10%-20%：中等风险水平
  - > 20%：下行风险较大

### 夏普比率
- **计算公式**：Sharpe = (R_p - R_f) / σ_p
- **解读**：
  - > 1.0：优秀，单位风险收益高
  - 0.5-1.0：良好
  - 0-0.5：一般
  - < 0：风险调整后收益为负

### Beta系数
- **定义**：基金相对于市场基准的波动敏感度
- **解读**：
  - < 1：波动小于市场
  - = 1：与市场同步
  - > 1：波动大于市场

### 集中度风险
- **前十大持仓占比**：
  - < 30%：分散度较高
  - 30%-50%：适中
  - > 60%：集中度较高，风险较大
- **单一行业占比**：
  - > 30%：行业集中度风险较高

## 分析原则

1. **全面性原则**：综合考虑多个风险维度，不遗漏重要风险点
2. **动态性原则**：风险指标需持续跟踪，关注变化趋势
3. **相关性原则**：分析风险指标之间的关联性
4. **实用性原则**：风险提示应具体明确，便于投资者理解"""
    
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        fund_info = context.get("fund_info", {})
        risk_metrics = context.get("risk_metrics", {})
        holdings = context.get("holdings", {})
        
        data_context = f"""## 基金基础信息
- 基金代码：{fund_info.get('fund_code', '未知')}
- 基金名称：{fund_info.get('fund_name', '未知')}
- 基金类型：{fund_info.get('fund_type', '未知')}
- 基金规模：{fund_info.get('current_scale', '未知')}亿元
- 成立日期：{fund_info.get('establish_date', '未知')}

## 波动率数据
- 年化波动率：{risk_metrics.get('annual_volatility', '未知')}%
- 日波动率：{risk_metrics.get('daily_volatility', '未知')}%
- 波动率趋势：{risk_metrics.get('volatility_trend', '未知')}

## 回撤数据
- 最大回撤：{risk_metrics.get('max_drawdown', '未知')}%
- 最大回撤发生日期：{risk_metrics.get('max_drawdown_date', '未知')}
- 最大回撤恢复天数：{risk_metrics.get('max_drawdown_recovery_days', '未知')}天
- 当前回撤：{risk_metrics.get('current_drawdown', '未知')}%

## 风险调整收益指标
- 夏普比率：{risk_metrics.get('sharpe_ratio', '未知')}
- 卡玛比率：{risk_metrics.get('calmar_ratio', '未知')}
- 索提诺比率：{risk_metrics.get('sortino_ratio', '未知')}

## 系统性风险指标
- Beta系数：{risk_metrics.get('beta', '未知')}
- 相关系数：{risk_metrics.get('correlation', '未知')}
- 基准指数：{risk_metrics.get('benchmark', '沪深300')}

## 集中度风险数据
- 前十大持仓占比：{holdings.get('top10_concentration', '未知')}%
- 单一行业最大占比：{holdings.get('single_industry_max', '未知')}%
- 行业数量：{holdings.get('industry_count', '未知')}个
- 持仓数据日期：{holdings.get('report_date', '未知')}

## 风险预警信息
{self._format_risk_alerts(risk_metrics.get('risk_alerts', []))}

## 补充信息
{context.get('additional_info', '无')}"""
        
        return f"""请对以上基金进行风险分析。

{data_context}

请按照分析框架逐步分析，重点关注：
1. 主要风险来源识别
2. 风险指标的综合评估
3. 潜在风险点提示
4. 风险等级评定

输出符合格式要求的JSON结果。"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        base_schema = StandardOutputSchema.get_base_schema(1.0, 5.0)
        
        base_schema["properties"]["details"] = {
            "type": "object",
            "required": [
                "risk_level",
                "annual_volatility",
                "max_drawdown",
                "max_drawdown_date",
                "sharpe_ratio",
                "beta",
                "top10_concentration",
                "single_industry_max",
                "risk_alerts"
            ],
            "properties": {
                "risk_level": {
                    "type": "string",
                    "enum": ["低", "中", "高"],
                    "description": "风险等级"
                },
                "annual_volatility": {
                    "type": "number",
                    "description": "年化波动率（%）"
                },
                "max_drawdown": {
                    "type": "number",
                    "description": "最大回撤（%）"
                },
                "max_drawdown_date": {
                    "type": "string",
                    "description": "最大回撤发生日期"
                },
                "sharpe_ratio": {
                    "type": "number",
                    "description": "夏普比率"
                },
                "beta": {
                    "type": "number",
                    "description": "Beta系数"
                },
                "top10_concentration": {
                    "type": "number",
                    "description": "前十大持仓占比（%）"
                },
                "single_industry_max": {
                    "type": "number",
                    "description": "单一行业最大占比（%）"
                },
                "risk_alerts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "风险预警信息列表"
                }
            }
        }
        
        return base_schema
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return CommonTemplates.get_output_format_instruction(schema)
    
    def _format_risk_alerts(self, alerts: list) -> str:
        """格式化风险预警信息"""
        if not alerts:
            return "暂无风险预警"
        
        return "\n".join([f"- {alert}" for alert in alerts])


RISK_SYSTEM_PROMPT = RiskPromptTemplate().get_system_prompt()
RISK_OUTPUT_SCHEMA = RiskPromptTemplate().get_output_schema()
