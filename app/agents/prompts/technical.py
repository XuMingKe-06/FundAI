"""
技术分析师提示词模板
负责均线系统分析、MACD指标解读、RSI指标分析、趋势判断
"""
from typing import Dict, Any
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates
)


class TechnicalPromptTemplate(PromptTemplate):
    """
    技术分析师提示词模板
    
    分析维度：
    1. 均线系统分析（MA20/MA60/MA120）
    2. MACD指标解读
    3. RSI指标分析
    4. 估值分位数评估
    5. 走势预测
    """
    
    def __init__(self):
        super().__init__(
            agent_type="technical",
            agent_name="技术分析师",
            score_range=(1, 5)
        )
    
    def get_system_prompt(self) -> str:
        role_def = CommonTemplates.get_role_definition_template(
            role_name="基金技术分析师",
            expertise=[
                "均线系统分析与趋势判断",
                "MACD指标解读与买卖信号识别",
                "RSI超买超卖区间分析",
                "布林带分析与波动率评估",
                "KDJ指标分析与超买超卖判断",
                "支撑位/阻力位识别",
                "估值分位数与安全边际评估",
                "短期走势预测与目标区间计算"
            ]
        )
        
        analysis_framework = CommonTemplates.get_analysis_framework_template([
            {
                "name": "均线系统分析",
                "description": "计算MA20、MA60、MA120，判断均线排列形态（多头排列/空头排列/震荡）"
            },
            {
                "name": "MACD指标分析",
                "description": "计算MACD线、信号线、柱状图，识别金叉/死叉信号，判断多空趋势"
            },
            {
                "name": "RSI指标分析",
                "description": "计算14日RSI，判断超买（>70）/超卖（<30）区间，评估短期动能"
            },
            {
                "name": "布林带分析",
                "description": "计算布林带上中下轨，判断价格突破信号和波动率变化"
            },
            {
                "name": "KDJ指标分析",
                "description": "计算KDJ指标，判断超买超卖和金叉死叉信号"
            },
            {
                "name": "支撑阻力位分析",
                "description": "识别关键支撑位和阻力位，判断当前位置与关键价位的关系"
            },
            {
                "name": "估值分位数评估",
                "description": "计算当前净值在历史数据中的分位数，评估估值安全边际"
            },
            {
                "name": "走势预测",
                "description": "综合技术指标，预测未来15天走势方向和目标区间"
            },
            {
                "name": "综合评分计算",
                "description": "基于各技术指标信号，计算综合技术面评分"
            }
        ])
        
        scoring_criteria = CommonTemplates.get_scoring_criteria_template([
            {"range": "5.0分", "description": "均线多头排列，MACD金叉或强势多头，RSI中性区间（40-60），估值处于低位（<20%分位）"},
            {"range": "4.0-4.9分", "description": "均线多头排列或震荡偏强，MACD多头，RSI未超买，估值合理偏低"},
            {"range": "3.0-3.9分", "description": "均线震荡，MACD中性，RSI中性区间，估值处于中间区域"},
            {"range": "2.0-2.9分", "description": "均线空头排列或震荡偏弱，MACD空头，RSI偏高或偏低，估值偏高"},
            {"range": "1.0-1.9分", "description": "均线空头排列，MACD死叉或强势空头，RSI超买，估值处于高位（>80%分位）"}
        ])
        
        output_format = self._get_output_format_instruction()
        
        return f"""{role_def}

{analysis_framework}

{scoring_criteria}

{output_format}

## 技术指标说明

### 均线系统
- **多头排列**：当前净值 > MA20 > MA60 > MA120，表示上升趋势
- **空头排列**：当前净值 < MA20 < MA60 < MA120，表示下降趋势
- **震荡**：均线交织，无明确方向

### MACD指标
- **金叉**：MACD线从下向上穿过信号线，买入信号
- **死叉**：MACD线从上向下穿过信号线，卖出信号
- **多头**：MACD线在信号线上方
- **空头**：MACD线在信号线下方
- **柱状图**：正值表示多头动能，负值表示空头动能

### RSI指标
- **超买区间**：RSI > 70，可能面临回调
- **超卖区间**：RSI < 30，可能出现反弹
- **中性区间**：40 < RSI < 60，趋势相对稳定

### 估值分位数
- **低估区间**：< 20%分位，安全边际较高
- **合理偏低**：30%-50%分位
- **合理偏高**：50%-70%分位
- **高估区间**：> 80%分位，风险较高

## 分析原则

1. **趋势优先**：均线系统是判断大趋势的核心指标
2. **信号确认**：单一指标信号需其他指标配合确认
3. **风险意识**：高估值区域需谨慎，低估值区域可积极
4. **动态跟踪**：技术指标需持续跟踪，及时调整判断

## 数据诚实规则
1. 如果提供的数据中包含 '数据不可用'、'暂不支持' 或 ToolResult.fail 的结果，你必须在分析中明确标注该数据不可用
2. 绝对不得在数据不足时编造或推测分析结论
3. 如果关键数据缺失，应降低 confidence 评分并在 summary 中说明
4. 不得将默认值或占位数据当作真实数据进行分析"""
    
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """获取用户提示词"""
        nav_data = context.get("nav_data", {})
        indicators = context.get("indicators", {})
        
        data_context = f"""## 基金基础信息
- 基金代码：{context.get('fund_code', '未知')}
- 基金名称：{context.get('fund_name', '未知')}
- 当前净值：{nav_data.get('current_nav', '未知')}
- 净值日期：{nav_data.get('nav_date', '未知')}
- 数据覆盖周期：{nav_data.get('data_period', '未知')}个交易日

## 均线系统数据
- MA20：{indicators.get('ma20', '未知')}
- MA60：{indicators.get('ma60', '未知')}
- MA120：{indicators.get('ma120', '未知')}
- 均线形态：{indicators.get('ma_trend', '未知')}

## MACD指标数据
- MACD值（DIF）：{indicators.get('macd_value', '未知')}
- 信号线（DEA）：{indicators.get('macd_signal', '未知')}
- 柱状图（MACD Histogram）：{indicators.get('macd_histogram', '未知')}
- MACD信号类型：{indicators.get('macd_signal_type', '未知')}

## RSI指标数据
- RSI(14)：{indicators.get('rsi_14', '未知')}
- RSI状态：{indicators.get('rsi_status', '未知')}

## 估值分位数数据
- 当前估值分位数：{indicators.get('valuation_percentile', '未知')}%
- 估值状态：{indicators.get('valuation_status', '未知')}
- 历史最低净值：{nav_data.get('min_nav', '未知')}
- 历史最高净值：{nav_data.get('max_nav', '未知')}

## 布林带数据
{self._format_bollinger(indicators.get('bollinger'))}

## KDJ指标数据
{self._format_kdj(indicators.get('kdj'))}

## 支撑阻力位数据
{self._format_support_resistance(indicators.get('support_resistance'))}

## 近期净值走势
{self._format_nav_history(nav_data.get('recent_nav', []))}

## 补充信息
{context.get('additional_info', '无')}"""
        
        return f"""请对以上基金进行技术面分析。

{data_context}

请按照分析框架逐步分析，重点关注：
1. 当前趋势方向及强度
2. 技术指标信号的一致性
3. 估值安全边际
4. 未来15天走势预测

输出符合格式要求的JSON结果。"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出JSON Schema"""
        base_schema = StandardOutputSchema.get_base_schema(1.0, 5.0)
        
        base_schema["properties"]["details"] = {
            "type": "object",
            "required": [
                "trend_direction",
                "ma20",
                "ma60",
                "ma120",
                "macd_signal",
                "macd_value",
                "macd_histogram",
                "rsi_14",
                "valuation_percentile",
                "prediction_15d",
                "current_nav",
                "data_points"
            ],
            "properties": {
                "trend_direction": {
                    "type": "string",
                    "enum": ["上升", "下降", "震荡"],
                    "description": "趋势方向"
                },
                "ma20": {
                    "type": "number",
                    "description": "20日均线值"
                },
                "ma60": {
                    "type": "number",
                    "description": "60日均线值"
                },
                "ma120": {
                    "type": "number",
                    "description": "120日均线值"
                },
                "macd_signal": {
                    "type": "string",
                    "enum": ["金叉", "死叉", "多头", "空头", "数据不足"],
                    "description": "MACD信号类型"
                },
                "macd_value": {
                    "type": "number",
                    "description": "MACD值（DIF）"
                },
                "macd_histogram": {
                    "type": "number",
                    "description": "MACD柱状图值"
                },
                "rsi_14": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "14日RSI值"
                },
                "valuation_percentile": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "估值分位数（%）"
                },
                "prediction_15d": {
                    "type": "object",
                    "description": "未来15天走势预测",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["震荡上行", "震荡下行", "横盘震荡"],
                            "description": "预测方向"
                        },
                        "target_low": {
                            "type": "number",
                            "description": "目标区间下限"
                        },
                        "target_high": {
                            "type": "number",
                            "description": "目标区间上限"
                        }
                    }
                },
                "current_nav": {
                    "type": "number",
                    "description": "当前净值"
                },
                "data_points": {
                    "type": "integer",
                    "description": "分析数据点数量"
                }
            }
        }
        
        return base_schema
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式说明"""
        schema = self.get_output_schema()
        return CommonTemplates.get_output_format_instruction(schema)
    
    def _format_nav_history(self, nav_list: list) -> str:
        if not nav_list:
            return "暂无净值历史数据"

        lines = ["日期 | 净值 | 涨跌幅"]
        lines.append("-" * 40)
        for item in nav_list[-10:]:
            date = item.get('date', '未知')
            nav = item.get('nav', '未知')
            change = item.get('change_pct', '未知')
            lines.append(f"{date} | {nav} | {change}%")

        return "\n".join(lines)

    def _format_bollinger(self, bollinger: dict) -> str:
        if not bollinger:
            return "布林带数据不可用"
        return (
            f"- 上轨: {bollinger.get('upper', '未知')}\n"
            f"- 中轨: {bollinger.get('middle', '未知')}\n"
            f"- 下轨: {bollinger.get('lower', '未知')}\n"
            f"- 带宽: {bollinger.get('bandwidth', '未知')}\n"
            f"- %B指标: {bollinger.get('percent_b', '未知')}\n"
            f"- 信号: {bollinger.get('signal', '未知')}"
        )

    def _format_kdj(self, kdj: dict) -> str:
        if not kdj:
            return "KDJ数据不可用"
        return (
            f"- K值: {kdj.get('k', '未知')}\n"
            f"- D值: {kdj.get('d', '未知')}\n"
            f"- J值: {kdj.get('j', '未知')}\n"
            f"- 信号: {kdj.get('signal', '未知')}"
        )

    def _format_support_resistance(self, sr: dict) -> str:
        if not sr:
            return "支撑阻力位数据不可用"
        return (
            f"- 支撑位: {sr.get('support_levels', '未知')}\n"
            f"- 阻力位: {sr.get('resistance_levels', '未知')}\n"
            f"- 最近支撑: {sr.get('nearest_support', '未知')}\n"
            f"- 最近阻力: {sr.get('nearest_resistance', '未知')}\n"
            f"- 当前位置: {sr.get('current_position', '未知')}"
        )


TECHNICAL_SYSTEM_PROMPT = TechnicalPromptTemplate().get_system_prompt()
TECHNICAL_OUTPUT_SCHEMA = TechnicalPromptTemplate().get_output_schema()
