"""
成本分析师提示词模板
负责费率结构分析、成本矩阵计算、短线可行性评估
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates
)


class CostPromptTemplate(PromptTemplate):
    """
    成本分析师提示词模板
    
    分析维度：
    1. 申购费率分析
    2. 赎回费率阶梯分析
    3. 成本矩阵计算
    4. 短线可行性评估
    5. 最优持有期推荐
    """
    
    def __init__(self):
        super().__init__(
            agent_type="cost",
            agent_name="成本分析师",
            score_range=(1, 5)
        )
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        role_def = CommonTemplates.get_role_definition_template(
            role_name="基金成本分析师",
            expertise=[
                "基金费率结构分析与比较",
                "赎回费率阶梯解读与成本优化",
                "成本矩阵计算与盈亏平衡分析",
                "短线投资成本可行性评估",
                "最优持有期策略推荐"
            ]
        )
        
        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "申购费率分析",
                "description": "分析申购费率原价、平台折扣后费率，评估申购成本"
            },
            {
                "name": "赎回费率阶梯分析",
                "description": "解读赎回费率阶梯结构，分析不同持有期的赎回成本"
            },
            {
                "name": "成本矩阵计算",
                "description": "计算各持有期的总费率、盈亏平衡点，构建成本矩阵"
            },
            {
                "name": "短线可行性评估",
                "description": "基于预期收益率，评估短线（<=30天）投资的成本可行性"
            },
            {
                "name": "最优持有期推荐",
                "description": "综合成本和收益，推荐最优持有期"
            }
        ])
        
        scoring_criteria = CommonTemplates.get_scoring_criteria_template([
            {"range": "5.0分", "description": "所有短线持有期都盈利，平均净收益率>3%，成本极低"},
            {"range": "4.0-4.9分", "description": "大部分短线持有期盈利，平均净收益率>2%，成本可接受"},
            {"range": "3.0-3.9分", "description": "部分短线持有期盈利，平均净收益率>1%，成本中等"},
            {"range": "2.0-2.9分", "description": "少数短线持有期盈利，平均净收益率<1%，成本较高"},
            {"range": "1.0-1.9分", "description": "所有短线持有期都亏损，成本极高，不具备可行性"}
        ])
        
        output_format = self._get_output_format_instruction()
        
        return f"""{role_def}

{analysis_framework}

{scoring_criteria}

{output_format}

## 费率结构说明

### 申购费率
- **原价费率**：通常为1.0%-1.5%
- **平台折扣**：代销平台通常提供1折优惠，约0.1%-0.15%
- **大额优惠**：超过一定金额可能有额外优惠

### 赎回费率阶梯（行业标准）
| 持有期 | 赎回费率 |
|--------|----------|
| 不满7天 | 1.50% |
| 7-30天 | 0.75% |
| 30天-1年 | 0.50% |
| 1-2年 | 0.25% |
| 2年以上 | 0.00% |

### 管理费用
- **管理费**：通常0.5%-1.5%/年（按日计提）
- **托管费**：通常0.1%-0.25%/年
- **销售服务费**：C类份额收取，约0.4%/年

## 成本计算公式

### 总费率计算
```
总费率 = 申购费率 + 赎回费率
```

### 盈亏平衡点计算
```
盈亏平衡点 = 总费率 / (1 - 总费率)
```
即需要达到的收益率才能覆盖交易成本。

### 净收益率计算
```
净收益率 = 预期毛收益率 - 总费率
```

## 短线可行性判断标准

- **具备成本可行性**：所有短线持有期净收益为正
- **部分具备成本可行性**：部分短线持有期净收益为正
- **不具备成本可行性**：所有短线持有期净收益为负

## 分析原则

1. **精确性原则**：费率数据需准确，影响成本计算结果
2. **实用性原则**：结论应指导实际投资决策
3. **动态性原则**：关注费率优惠政策变化
4. **全面性原则**：考虑所有交易成本，包括隐性成本"""
    
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        fund_info = context.get("fund_info", {})
        fees = context.get("fees", {})
        cost_matrix = context.get("cost_matrix", [])
        expected_return = context.get('expected_return', 0.042)
        
        data_context = f"""## 基金基础信息
- 基金代码：{fund_info.get('fund_code', '未知')}
- 基金名称：{fund_info.get('fund_name', '未知')}
- 基金类型：{fund_info.get('fund_type', '未知')}
- 份额类别：{fund_info.get('share_class', 'A类')}

## 费率信息
- 申购费率（原价）：{fees.get('purchase_fee_original', '未知')}%
- 申购费率（折扣后）：{fees.get('purchase_fee_discounted', '未知')}%
- 管理费率：{fees.get('management_fee', '未知')}%/年
- 托管费率：{fees.get('custody_fee', '未知')}%/年
- 销售服务费：{fees.get('sales_service_fee', '未知')}%/年

## 赎回费率阶梯
{self._format_redemption_ladder(fees.get('redemption_ladder', []))}

## 成本矩阵
{self._format_cost_matrix(cost_matrix)}

## 预期收益假设
- 预期毛收益率：{expected_return * 100:.2f}%

## 短线可行性分析
{self._format_feasibility_analysis(context.get('feasibility_analysis', {}))}

## 补充信息
{context.get('additional_info', '无')}"""
        
        return f"""请对以上基金进行成本分析。

{data_context}

请按照分析框架逐步分析，重点关注：
1. 各持有期的成本结构
2. 短线投资的成本可行性
3. 最优持有期推荐
4. 成本优化建议

输出符合格式要求的JSON结果。"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        base_schema = StandardOutputSchema.get_base_schema(1.0, 5.0)
        
        base_schema["properties"]["details"] = {
            "type": "object",
            "required": [
                "purchase_fee_rate",
                "redemption_fee_ladder",
                "cost_matrix",
                "short_term_feasibility",
                "feasibility_details",
                "recommended_holding_period",
                "expected_return"
            ],
            "properties": {
                "purchase_fee_rate": {
                    "type": "number",
                    "description": "申购费率（折扣后）"
                },
                "redemption_fee_ladder": {
                    "type": "array",
                    "description": "赎回费率阶梯",
                    "items": {
                        "type": "object",
                        "properties": {
                            "min_days": {"type": "integer", "description": "最小持有天数"},
                            "max_days": {"type": "integer", "description": "最大持有天数，null表示无上限"},
                            "fee_rate": {"type": "number", "description": "费率"},
                            "description": {"type": "string", "description": "持有期描述"}
                        }
                    }
                },
                "cost_matrix": {
                    "type": "array",
                    "description": "成本矩阵",
                    "items": {
                        "type": "object",
                        "properties": {
                            "holding_period": {"type": "string", "description": "持有期"},
                            "holding_days": {"type": "integer", "description": "持有天数"},
                            "purchase_fee": {"type": "number", "description": "申购费率"},
                            "redemption_fee": {"type": "number", "description": "赎回费率"},
                            "total_fee": {"type": "number", "description": "总费率"},
                            "breakeven": {"type": "number", "description": "盈亏平衡点"}
                        }
                    }
                },
                "short_term_feasibility": {
                    "type": "string",
                    "enum": ["具备成本可行性", "部分具备成本可行性", "不具备成本可行性", "无法评估"],
                    "description": "短线可行性评估结果"
                },
                "feasibility_details": {
                    "type": "object",
                    "description": "可行性评估详情",
                    "properties": {
                        "feasibility": {"type": "string"},
                        "analysis_text": {"type": "string"},
                        "net_returns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "holding_period": {"type": "string"},
                                    "net_return": {"type": "number"},
                                    "is_profitable": {"type": "boolean"}
                                }
                            }
                        }
                    }
                },
                "recommended_holding_period": {
                    "type": "string",
                    "description": "推荐持有期"
                },
                "expected_return": {
                    "type": "number",
                    "description": "预期毛收益率"
                }
            }
        }
        
        return base_schema
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return CommonTemplates.get_output_format_instruction(schema)
    
    def _format_redemption_ladder(self, ladder: list) -> str:
        """格式化赎回费率阶梯"""
        if not ladder:
            return "暂无赎回费率数据"
        
        lines = ["| 持有期 | 赎回费率 |"]
        lines.append("|--------|----------|")
        for item in ladder:
            desc = item.get('description', '未知')
            fee = item.get('fee_rate', 0)
            lines.append(f"| {desc} | {fee * 100:.2f}% |")
        
        return "\n".join(lines)
    
    def _format_cost_matrix(self, matrix: list) -> str:
        """格式化成本矩阵"""
        if not matrix:
            return "暂无成本矩阵数据"
        
        lines = ["| 持有期 | 申购费 | 赎回费 | 总费率 | 盈亏平衡点 |"]
        lines.append("|--------|--------|--------|--------|------------|")
        for item in matrix:
            period = item.get('holding_period', '未知')
            purchase = item.get('purchase_fee', 0) * 100
            redemption = item.get('redemption_fee', 0) * 100
            total = item.get('total_fee', 0) * 100
            breakeven = item.get('breakeven', 0) * 100
            lines.append(f"| {period} | {purchase:.2f}% | {redemption:.2f}% | {total:.2f}% | {breakeven:.2f}% |")
        
        return "\n".join(lines)
    
    def _format_feasibility_analysis(self, analysis: dict) -> str:
        """格式化可行性分析"""
        if not analysis:
            return "暂无可行性分析数据"
        
        lines = [
            f"- 可行性结论：{analysis.get('feasibility', '未知')}",
            f"- 分析说明：{analysis.get('analysis_text', '无')}",
            f"- 盈利方案数：{analysis.get('profitable_count', 0)}/{analysis.get('total_count', 0)}"
        ]
        
        return "\n".join(lines)


COST_SYSTEM_PROMPT = CostPromptTemplate().get_system_prompt()
COST_OUTPUT_SCHEMA = CostPromptTemplate().get_output_schema()
