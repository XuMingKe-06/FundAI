"""
情绪分析师提示词模板
负责新闻舆情分析、资金流向分析、市场热度评估
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates
)


class SentimentPromptTemplate(PromptTemplate):
    """
    情绪分析师提示词模板
    
    分析维度：
    1. 新闻舆情分析
    2. 资金流向分析
    3. 市场热度评估
    4. 机构观点汇总
    
    注意：评分范围为 -5 到 +5，负值表示负面情绪，正值表示正面情绪
    """
    
    def __init__(self):
        super().__init__(
            agent_type="sentiment",
            agent_name="情绪分析师",
            score_range=(-5, 5)
        )
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        role_def = CommonTemplates.get_role_definition_template(
            role_name="市场情绪分析师",
            expertise=[
                "新闻舆情情感分析与热点追踪",
                "资金流向分析与主力动向监测",
                "社交媒体热度与投资者情绪分析",
                "机构观点汇总与评级变化追踪"
            ]
        )
        
        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "新闻舆情分析",
                "description": "收集相关新闻，分析正面/负面/中性比例，识别关键舆情事件"
            },
            {
                "name": "资金流向分析",
                "description": "分析近5日、近20日资金净流入/流出情况，判断主力资金动向"
            },
            {
                "name": "市场热度评估",
                "description": "评估社交媒体讨论热度、搜索指数，判断市场关注度"
            },
            {
                "name": "机构观点汇总",
                "description": "汇总券商研报、机构评级，分析买入/增持/中性/减持/卖出比例"
            },
            {
                "name": "综合情绪评分",
                "description": "综合各维度数据，计算情绪评分（-5到+5）"
            }
        ])
        
        scoring_criteria = CommonTemplates.get_scoring_criteria_template([
            {"range": "+3到+5分（非常正面）", "description": "舆情高度正面，资金大幅流入，市场热度高，机构一致看好"},
            {"range": "+1到+3分（偏正面）", "description": "舆情偏正面，资金净流入，市场关注度较高，机构观点积极"},
            {"range": "-1到+1分（中性）", "description": "舆情相对中性，资金流向平稳，市场关注度一般，机构观点分歧"},
            {"range": "-3到-1分（偏负面）", "description": "舆情偏负面，资金净流出，市场关注度下降，机构观点谨慎"},
            {"range": "-5到-3分（非常负面）", "description": "舆情高度负面，资金大幅流出，市场恐慌，机构一致看空"}
        ])
        
        output_format = self._get_output_format_instruction()
        
        return f"""{role_def}

{analysis_framework}

{scoring_criteria}

{output_format}

## 情绪分析维度说明

### 新闻舆情分析
- **正面新闻**：利好消息、业绩超预期、行业景气度提升等
- **负面新闻**：利空消息、业绩不及预期、行业风险等
- **中性新闻**：常规公告、人事变动、市场评论等
- **情感比率**：正面新闻数 / 负面新闻数（越大越好）

### 资金流向分析
- **净流入**：资金流入 > 资金流出，表示市场看好
- **净流出**：资金流入 < 资金流出，表示市场看空
- **关键指标**：
  - 近5日净流入：反映短期资金动向
  - 近20日净流入：反映中期资金趋势

### 市场热度评估
- **热度比率**：当前讨论热度 / 历史平均热度
  - > 1.5：高热度，市场关注度高
  - 0.8-1.5：中等热度
  - < 0.8：低热度，市场关注度低

### 机构观点汇总
- **买入/增持**：机构看好
- **中性**：机构观望
- **减持/卖出**：机构看空
- **一致性**：机构观点越一致，信号越强

## 评分权重配置

| 维度 | 权重 |
|------|------|
| 新闻舆情 | 30% |
| 资金流向 | 30% |
| 市场热度 | 20% |
| 机构观点 | 20% |

## 分析原则

1. **时效性原则**：情绪数据具有时效性，需关注最新变化
2. **多维度原则**：综合多个维度判断，避免单一指标误导
3. **反向思考原则**：极端情绪可能预示反转机会
4. **谨慎解读原则**：情绪指标仅供参考，需结合基本面分析

## 数据诚实规则
1. 如果提供的数据中包含 '数据不可用'、'暂不支持' 或 ToolResult.fail 的结果，你必须在分析中明确标注该数据不可用
2. 绝对不得在数据不足时编造或推测分析结论
3. 如果关键数据缺失，应降低 confidence 评分并在 summary 中说明
4. 不得将默认值或占位数据当作真实数据进行分析"""
    
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        fund_info = context.get("fund_info", {})
        news_data = context.get("news_data", {})
        flow_data = context.get("flow_data", {})
        social_data = context.get("social_data", {})
        institution_data = context.get("institution_data", {})
        
        data_context = f"""## 基金基础信息
- 基金代码：{fund_info.get('fund_code', '未知')}
- 基金名称：{fund_info.get('fund_name', '未知')}
- 基金类型：{fund_info.get('fund_type', '未知')}
- 基金规模：{fund_info.get('current_scale', '未知')}亿元

## 新闻舆情数据
- 新闻总数：{news_data.get('total', '未知')}条
- 正面新闻：{news_data.get('positive', '未知')}条
- 负面新闻：{news_data.get('negative', '未知')}条
- 中性新闻：{news_data.get('neutral', '未知')}条
- 情感比率：{news_data.get('sentiment_ratio', '未知')}

### 关键新闻标题
{self._format_key_news(news_data.get('key_news', []))}

## 资金流向数据
- 近5日净流入：{flow_data.get('net_inflow_5d', '未知')}亿元
- 近20日净流入：{flow_data.get('net_inflow_20d', '未知')}亿元
- 资金流向趋势：{flow_data.get('trend', '未知')}

## 市场热度数据
- 热度比率：{social_data.get('heat_ratio', '未知')}倍
- 热度等级：{social_data.get('level', '未知')}
- 讨论量变化：{social_data.get('discussion_change', '未知')}%

## 机构观点数据
- 买入评级：{institution_data.get('buy', '未知')}篇
- 增持评级：{institution_data.get('overweight', '未知')}篇
- 中性评级：{institution_data.get('neutral', '未知')}篇
- 减持评级：{institution_data.get('underweight', '未知')}篇
- 卖出评级：{institution_data.get('sell', '未知')}篇
- 研报总数：{institution_data.get('total_reports', '未知')}篇

## 补充信息
{context.get('additional_info', '无')}"""
        
        return f"""请对以上基金进行市场情绪分析。

{data_context}

请按照分析框架逐步分析，重点关注：
1. 当前市场情绪的整体方向
2. 资金流向的持续性
3. 机构观点的一致性
4. 潜在的情绪反转信号

输出符合格式要求的JSON结果。注意评分范围为 -5 到 +5。"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        base_schema = StandardOutputSchema.get_base_schema(-5.0, 5.0)
        
        base_schema["properties"]["details"] = {
            "type": "object",
            "required": [
                "sentiment_score",
                "news_analysis",
                "fund_flow",
                "social_heat",
                "institutional_views",
                "key_news"
            ],
            "properties": {
                "sentiment_score": {
                    "type": "number",
                    "minimum": -5,
                    "maximum": 5,
                    "description": "情绪评分（-5到+5）"
                },
                "news_analysis": {
                    "type": "object",
                    "description": "新闻舆情分析结果",
                    "properties": {
                        "total": {"type": "integer", "description": "新闻总数"},
                        "positive": {"type": "integer", "description": "正面新闻数"},
                        "negative": {"type": "integer", "description": "负面新闻数"},
                        "neutral": {"type": "integer", "description": "中性新闻数"},
                        "sentiment_ratio": {"type": "number", "description": "情感比率"}
                    }
                },
                "fund_flow": {
                    "type": "object",
                    "description": "资金流向数据",
                    "properties": {
                        "net_inflow_5d": {"type": "number", "description": "近5日净流入（亿元）"},
                        "net_inflow_20d": {"type": "number", "description": "近20日净流入（亿元）"},
                        "trend": {"type": "string", "description": "流向趋势"}
                    }
                },
                "social_heat": {
                    "type": "number",
                    "description": "社交热度比率"
                },
                "institutional_views": {
                    "type": "object",
                    "description": "机构观点汇总",
                    "properties": {
                        "buy": {"type": "integer", "description": "买入评级数"},
                        "overweight": {"type": "integer", "description": "增持评级数"},
                        "neutral": {"type": "integer", "description": "中性评级数"},
                        "underweight": {"type": "integer", "description": "减持评级数"},
                        "sell": {"type": "integer", "description": "卖出评级数"},
                        "total_reports": {"type": "integer", "description": "研报总数"}
                    }
                },
                "key_news": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键新闻标题列表"
                }
            }
        }
        
        return base_schema
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return CommonTemplates.get_output_format_instruction(schema)
    
    def _format_key_news(self, news_list: list) -> str:
        """格式化关键新闻"""
        if not news_list:
            return "暂无关键新闻"
        
        return "\n".join([f"- {news}" for news in news_list[:5]])


SENTIMENT_SYSTEM_PROMPT = SentimentPromptTemplate().get_system_prompt()
SENTIMENT_OUTPUT_SCHEMA = SentimentPromptTemplate().get_output_schema()
