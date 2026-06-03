"""
决策智能体提示词模板
负责汇总各分析智能体结果，生成双轨投资决策建议
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates
)


class DecisionPromptTemplate(PromptTemplate):
    """
    决策智能体提示词模板

    分析维度：
    1. 短线决策（<=30天）
    2. 长线决策（>=6个月）
    3. 置信度评估
    4. 投资建议生成

    注意：决策智能体不单独评分，输出双轨决策建议
    """

    def __init__(self):
        super().__init__(
            agent_type="decision",
            agent_name="投资决策顾问",
            score_range=(None, None)
        )

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        role_def = CommonTemplates.get_role_definition_template(
            role_name="投资决策顾问",
            expertise=[
                "多维度投资分析综合研判",
                "短线与长线双轨决策框架",
                "投资置信度评估与风险提示",
                "个性化投资建议生成"
            ]
        )

        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "汇总分析结果",
                "description": "整合基本面、技术面、风险、成本、情绪五个维度的分析结果"
            },
            {
                "name": "短线决策分析",
                "description": "基于技术面40%、情绪30%、风险20%、成本10%的权重计算短线综合得分，生成短线建议"
            },
            {
                "name": "长线决策分析",
                "description": "基于基本面50%、技术面30%、风险20%的权重计算长线综合得分，生成长线建议"
            },
            {
                "name": "置信度评估",
                "description": "基于评分偏离程度和各维度一致性计算置信度"
            },
            {
                "name": "生成投资建议",
                "description": "综合双轨决策，生成具体可执行的投资建议"
            }
        ])

        output_format = self._get_output_format_instruction()

        return f"""{role_def}

{analysis_framework}

{output_format}

## 双轨决策框架说明

### 短线决策（持有期<=30天）

**权重配置**：
| 维度 | 权重 | 说明 |
|------|------|------|
| 技术面 | 40% | 短线走势的核心判断依据 |
| 情绪 | 30% | 市场情绪影响短期波动 |
| 风险 | 20% | 风险控制是短线关键 |
| 成本 | 10% | 交易成本影响短线收益 |

**决策逻辑**：
- 综合得分 >= 3.5：建议买入
- 综合得分 2.5-3.5：建议持有观望
- 综合得分 < 2.5：建议卖出

**特殊判断**：
- 成本可行性为"不具备成本可行性"时，建议延长持有期
- 需结合止盈止损参考制定交易策略

### 长线决策（持有期>=6个月）

**权重配置**：
| 维度 | 权重 | 说明 |
|------|------|------|
| 基本面 | 50% | 长线投资的核心判断依据 |
| 技术面 | 30% | 估值安全边际参考 |
| 风险 | 20% | 风险控制始终重要 |

**决策逻辑**：
- 综合得分 >= 3.5：建议买入/定投
- 综合得分 2.5-3.5：建议持有
- 综合得分 < 2.5：建议减仓/卖出

**定投建议触发条件**：
- 综合得分 >= 3.5
- 估值分位数 < 40%
- 风险等级 != "高"

### 置信度计算方法

置信度 = 基础置信度 * 一致性因子 + 0.15

- **基础置信度**：得分偏离中性（3分）的程度
- **一致性因子**：各维度评分的标准差越小，一致性越高

置信度范围：0.3 - 0.95

## 分析原则

1. **双轨独立原则**：短线和长线决策独立判断，互不影响
2. **风险优先原则**：高风险情况下需谨慎，降低建议激进程度
3. **成本约束原则**：成本不可行时，短线建议需调整
4. **用户适配原则**：根据用户风险偏好调整建议

## 输出说明

决策智能体不输出单独的score，而是输出：
- short_term_decision：短线决策建议
- long_term_decision：长线决策建议
- agent_scores：各智能体评分汇总

## 数据诚实规则
1. 如果提供的数据中包含 '数据不可用'、'暂不支持' 或 ToolResult.fail 的结果，你必须在分析中明确标注该数据不可用
2. 绝对不得在数据不足时编造或推测分析结论
3. 如果关键数据缺失，应降低 confidence 评分并在 summary 中说明
4. 不得将默认值或占位数据当作真实数据进行分析"""

    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        fund_info = context.get("fund_info", {})
        agent_results = context.get("agent_results", {})
        user_preference = context.get("user_preference", "neutral")

        fundamental = agent_results.get("fundamental", {})
        technical = agent_results.get("technical", {})
        risk = agent_results.get("risk", {})
        cost = agent_results.get("cost", {})
        sentiment = agent_results.get("sentiment", {})

        data_context = f"""## 基金基础信息
- 基金代码：{fund_info.get('fund_code', '未知')}
- 基金名称：{fund_info.get('fund_name', '未知')}
- 基金类型：{fund_info.get('fund_type', '未知')}
- 基金规模：{fund_info.get('current_scale', '未知')}亿元

## 用户风险偏好
- 风险偏好类型：{self._get_preference_desc(user_preference)}

## 各维度分析结果汇总

### 基本面分析
- 评分：{fundamental.get('score', '未知')}分
- 摘要：{fundamental.get('summary', '无')}
- 基金经理：{fundamental.get('details', {}).get('fund_manager', '未知')}
- 从业年限：{fundamental.get('details', {}).get('management_experience_years', '未知')}年
- 超额收益：{fundamental.get('details', {}).get('alpha_1y', '未知')}%

### 技术面分析
- 评分：{technical.get('score', '未知')}分
- 摘要：{technical.get('summary', '无')}
- 趋势方向：{technical.get('details', {}).get('trend_direction', '未知')}
- MACD信号：{technical.get('details', {}).get('macd_signal', '未知')}
- RSI(14)：{technical.get('details', {}).get('rsi_14', '未知')}
- 估值分位数：{technical.get('details', {}).get('valuation_percentile', '未知')}%

### 风险分析
- 评分：{risk.get('score', '未知')}分
- 摘要：{risk.get('summary', '无')}
- 风险等级：{risk.get('details', {}).get('risk_level', '未知')}
- 年化波动率：{risk.get('details', {}).get('annual_volatility', '未知')}%
- 最大回撤：{risk.get('details', {}).get('max_drawdown', '未知')}%
- 夏普比率：{risk.get('details', {}).get('sharpe_ratio', '未知')}

### 成本分析
- 评分：{cost.get('score', '未知')}分
- 摘要：{cost.get('summary', '无')}
- 短线可行性：{cost.get('details', {}).get('short_term_feasibility', '未知')}
- 推荐持有期：{cost.get('details', {}).get('recommended_holding_period', '未知')}

### 情绪分析
- 评分：{sentiment.get('score', '未知')}分（范围-5到+5）
- 摘要：{sentiment.get('summary', '无')}
- 新闻舆情：{sentiment.get('details', {}).get('news_analysis', {}).get('sentiment_ratio', '未知')}
- 资金流向：{sentiment.get('details', {}).get('fund_flow', {}).get('trend', '未知')}

## 走势数据
- 当前净值：{technical.get('details', {}).get('current_nav', '未知')}
- 预测方向：{technical.get('details', {}).get('prediction_15d', {}).get('direction', '未知')}

请基于以上分析结果，按照双轨决策框架生成投资建议。"""
        return self._add_previous_report_section(context, data_context)

    def _add_previous_report_section(self, context: Dict[str, Any], data_context: str) -> str:
        """如果存在历史分析报告，添加到提示词中供参考"""
        previous_report = context.get("previous_report")
        if not previous_report:
            return data_context

        prev_short = previous_report.get("short_term_decision", {})
        prev_long = previous_report.get("long_term_decision", {})
        prev_scores = previous_report.get("agent_scores", {})
        prev_date = previous_report.get("analysis_date", "未知")
        risk_alerts = previous_report.get("risk_alerts", [])

        risk_text = ""
        if risk_alerts:
            risk_lines = "\n".join(f"- {alert}" for alert in risk_alerts)
            risk_text = f"""### 上次分析的风险提示
{risk_lines}

"""

        data_context += f"""

## 历史分析参考（{prev_date}）

### 上次分析的决策建议
- 短线方向：{prev_short.get('direction', '未知')}
- 短线置信度：{prev_short.get('confidence', '未知')}
- 长线方向：{prev_long.get('direction', '未知')}
- 长线置信度：{prev_long.get('confidence', '未知')}

### 上次分析的各维度评分
- 基本面：{prev_scores.get('fundamental', '未知')}分
- 技术面：{prev_scores.get('technical', '未知')}分
- 风险：{prev_scores.get('risk', '未知')}分
- 成本：{prev_scores.get('cost', '未知')}分
- 情绪：{prev_scores.get('sentiment', '未知')}分

{risk_text}请参考上述历史分析数据，结合当前最新分析结果，判断该基金的投资价值是否发生变化，并给出新的决策建议。如果当前分析与历史结论一致，请说明趋势延续；如果发生变化，请重点分析变化原因。"""
        return data_context

    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        return {
            "type": "object",
            "required": ["summary", "details"],
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "综合研判摘要"
                },
                "details": {
                    "type": "object",
                    "required": [
                        "short_term_decision",
                        "long_term_decision",
                        "agent_scores",
                        "user_preference",
                        "trend_data"
                    ],
                    "properties": {
                        "short_term_decision": {
                            "type": "object",
                            "description": "短线决策建议",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "enum": ["buy", "hold", "sell"],
                                    "description": "操作方向"
                                },
                                "holding_period": {
                                    "type": "string",
                                    "description": "推荐持有期"
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "置信度（0-1）"
                                },
                                "reasons": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "决策理由列表"
                                },
                                "stop_profit": {
                                    "type": "string",
                                    "description": "止盈参考"
                                },
                                "stop_loss": {
                                    "type": "string",
                                    "description": "止损参考"
                                },
                                "cost_feasibility": {
                                    "type": "string",
                                    "description": "成本可行性评估"
                                }
                            }
                        },
                        "long_term_decision": {
                            "type": "object",
                            "description": "长线决策建议",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "enum": ["buy", "hold", "sell"],
                                    "description": "操作方向"
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "置信度（0-1）"
                                },
                                "reasons": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "决策理由列表"
                                },
                                "dip_investment_suggestion": {
                                    "type": "string",
                                    "nullable": True,
                                    "description": "定投建议"
                                }
                            }
                        },
                        "agent_scores": {
                            "type": "object",
                            "description": "各智能体评分汇总",
                            "properties": {
                                "fundamental": {"type": "number"},
                                "technical": {"type": "number"},
                                "risk": {"type": "number"},
                                "cost": {"type": "number"},
                                "sentiment": {"type": "number"}
                            }
                        },
                        "user_preference": {
                            "type": "string",
                            "enum": ["conservative", "neutral", "aggressive"],
                            "description": "用户风险偏好"
                        },
                        "trend_data": {
                            "type": "object",
                            "description": "走势数据",
                            "properties": {
                                "current_nav": {"type": "number"},
                                "prediction_direction": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }

    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return f"""请严格按照以下JSON格式输出分析结果：

```json
{schema}
```

注意事项：
1. 决策智能体不输出score字段
2. summary应简洁概括双轨决策结论
3. short_term_decision包含短线操作建议（<=30天）
4. long_term_decision包含长线操作建议（>=6个月）
5. reasons最多5条理由
6. confidence为0-1之间的小数"""

    def _get_preference_desc(self, preference: str) -> str:
        """获取风险偏好描述"""
        desc_map = {
            "conservative": "保守型（偏好低风险）",
            "neutral": "平衡型（偏好中等风险）",
            "aggressive": "激进型（偏好高风险）"
        }
        return desc_map.get(preference, "平衡型")


DECISION_SYSTEM_PROMPT = DecisionPromptTemplate().get_system_prompt()
DECISION_OUTPUT_SCHEMA = DecisionPromptTemplate().get_output_schema()
