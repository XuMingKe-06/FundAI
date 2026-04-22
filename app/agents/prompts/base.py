"""
提示词基类和通用模板
定义所有智能体提示词的基类和通用输出格式
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class OutputFormat(Enum):
    """输出格式枚举"""
    STANDARD = "standard"
    DETAILED = "detailed"
    SUMMARY = "summary"


class PromptTemplate(ABC):
    """
    提示词模板基类
    
    所有智能体提示词都应继承此类，实现具体的提示词生成逻辑
    """
    
    def __init__(
        self,
        agent_type: str,
        agent_name: str,
        score_range: tuple = (1, 5)
    ):
        """
        初始化提示词模板
        
        Args:
            agent_type: 智能体类型标识
            agent_name: 智能体名称
            score_range: 评分范围，默认(1, 5)
        """
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.score_range = score_range
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        获取系统提示词
        
        Returns:
            系统提示词字符串
        """
        pass
    
    @abstractmethod
    def get_user_prompt(self, context: Dict[str, Any]) -> str:
        """
        获取用户提示词
        
        Args:
            context: 分析上下文数据
            
        Returns:
            用户提示词字符串
        """
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """
        获取输出JSON Schema
        
        Returns:
            JSON Schema字典
        """
        pass
    
    def build_prompt(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        构建完整提示词
        
        Args:
            context: 分析上下文数据
            
        Returns:
            包含system和user提示词的字典
        """
        return {
            "system": self.get_system_prompt(),
            "user": self.get_user_prompt(context)
        }


class StandardOutputSchema:
    """标准输出格式定义"""
    
    @staticmethod
    def get_base_schema(score_min: float = 1.0, score_max: float = 5.0) -> Dict[str, Any]:
        """
        获取基础输出Schema
        
        Args:
            score_min: 评分最小值
            score_max: 评分最大值
            
        Returns:
            基础Schema字典
        """
        return {
            "type": "object",
            "required": ["score", "summary", "details"],
            "properties": {
                "score": {
                    "type": "number",
                    "minimum": score_min,
                    "maximum": score_max,
                    "description": f"综合评分，范围{score_min}-{score_max}"
                },
                "summary": {
                    "type": "string",
                    "description": "分析摘要，简洁概括主要结论"
                },
                "details": {
                    "type": "object",
                    "description": "详细分析数据"
                }
            }
        }
    
    @staticmethod
    def get_thinking_schema() -> Dict[str, Any]:
        """获取思考过程Schema"""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "string", "description": "分析步骤描述"},
                    "finding": {"type": "string", "description": "该步骤的发现"}
                }
            },
            "description": "分析思考过程"
        }


class CommonTemplates:
    """通用模板片段"""
    
    @staticmethod
    def get_role_definition_template(role_name: str, expertise: List[str]) -> str:
        """
        生成角色定义模板
        
        Args:
            role_name: 角色名称
            expertise: 专业领域列表
            
        Returns:
            角色定义字符串
        """
        expertise_str = "、".join(expertise)
        return f"""你是一位专业的{role_name}，具备以下专业能力：
{expertise_str}

你的职责是基于客观数据进行专业分析，提供准确、有洞察力的评估结论。"""
    
    @staticmethod
    def get_output_format_instruction(schema: Dict[str, Any]) -> str:
        """
        生成输出格式说明
        
        Args:
            schema: 输出Schema
            
        Returns:
            输出格式说明字符串
        """
        return f"""请严格按照以下JSON格式输出分析结果：

```json
{schema}
```

注意事项：
1. score必须是数值类型，在指定范围内
2. summary应简洁明了，控制在50-100字
3. details应包含完整的分析数据
4. 所有数值保留2位小数"""
    
    @staticmethod
    def get_analysis_framework_template(
        steps: List[Dict[str, str]]
    ) -> str:
        """
        生成分析框架模板
        
        Args:
            steps: 分析步骤列表，每项包含name和description
            
        Returns:
            分析框架字符串
        """
        steps_str = "\n".join([
            f"{i+1}. **{step['name']}**：{step['description']}"
            for i, step in enumerate(steps)
        ])
        return f"""请按以下分析框架进行分析：

{steps_str}

每个步骤都应基于数据得出结论，并在最终输出中体现。"""
    
    @staticmethod
    def get_scoring_criteria_template(
        criteria: List[Dict[str, Any]]
    ) -> str:
        """
        生成评分标准模板
        
        Args:
            criteria: 评分标准列表
            
        Returns:
            评分标准字符串
        """
        criteria_str = "\n".join([
            f"- {c['range']}: {c['description']}"
            for c in criteria
        ])
        return f"""评分标准：

{criteria_str}

评分应综合考虑各维度因素，给出客观公正的综合评分。"""
    
    @staticmethod
    def get_data_context_template(
        data_description: str
    ) -> str:
        """
        生成数据上下文模板
        
        Args:
            data_description: 数据描述
            
        Returns:
            数据上下文字符串
        """
        return f"""以下是供分析的数据：

{data_description}

请基于以上数据进行专业分析。"""
    
    @staticmethod
    def get_constraints_template(
        constraints: List[str]
    ) -> str:
        """
        生成约束条件模板
        
        Args:
            constraints: 约束条件列表
            
        Returns:
            约束条件字符串
        """
        constraints_str = "\n".join([f"- {c}" for c in constraints])
        return f"""分析约束条件：

{constraints_str}"""


class AnalysisDimension:
    """分析维度定义"""
    
    FUNDAMENTAL = {
        "name": "基本面分析",
        "dimensions": [
            {
                "key": "fund_manager",
                "name": "基金经理能力",
                "factors": ["从业年限", "历史业绩", "管理规模", "投资风格"]
            },
            {
                "key": "holdings",
                "name": "持仓结构",
                "factors": ["前十大持仓占比", "行业分布", "持仓集中度", "换手率"]
            },
            {
                "key": "performance",
                "name": "业绩表现",
                "factors": ["累计收益率", "超额收益", "信息比率", "同类排名"]
            }
        ]
    }
    
    TECHNICAL = {
        "name": "技术面分析",
        "dimensions": [
            {
                "key": "ma_system",
                "name": "均线系统",
                "factors": ["MA20", "MA60", "MA120", "均线排列形态"]
            },
            {
                "key": "macd",
                "name": "MACD指标",
                "factors": ["DIF线", "DEA线", "柱状图", "金叉死叉信号"]
            },
            {
                "key": "rsi",
                "name": "RSI指标",
                "factors": ["RSI数值", "超买超卖区间", "背离信号"]
            },
            {
                "key": "valuation",
                "name": "估值分位数",
                "factors": ["当前估值位置", "历史分位数", "安全边际"]
            }
        ]
    }
    
    RISK = {
        "name": "风险分析",
        "dimensions": [
            {
                "key": "volatility",
                "name": "波动率分析",
                "factors": ["年化波动率", "日波动率", "波动率趋势"]
            },
            {
                "key": "drawdown",
                "name": "回撤分析",
                "factors": ["最大回撤", "回撤持续时间", "恢复速度"]
            },
            {
                "key": "risk_adjusted",
                "name": "风险调整收益",
                "factors": ["夏普比率", "卡玛比率", "索提诺比率"]
            },
            {
                "key": "beta",
                "name": "系统性风险",
                "factors": ["Beta系数", "相关性", "市场敏感度"]
            }
        ]
    }
    
    COST = {
        "name": "成本分析",
        "dimensions": [
            {
                "key": "purchase_fee",
                "name": "申购费用",
                "factors": ["申购费率", "平台折扣", "大额优惠"]
            },
            {
                "key": "redemption_fee",
                "name": "赎回费用",
                "factors": ["赎回费率阶梯", "持有期要求", "免赎费条件"]
            },
            {
                "key": "management_fee",
                "name": "管理费用",
                "factors": ["管理费率", "托管费率", "销售服务费"]
            }
        ]
    }
    
    SENTIMENT = {
        "name": "情绪分析",
        "dimensions": [
            {
                "key": "news",
                "name": "新闻舆情",
                "factors": ["新闻数量", "正面/负面比例", "关键词热度"]
            },
            {
                "key": "fund_flow",
                "name": "资金流向",
                "factors": ["净流入/流出", "大单动向", "北向资金"]
            },
            {
                "key": "social_heat",
                "name": "市场热度",
                "factors": ["讨论热度", "搜索指数", "关注度变化"]
            }
        ]
    }
