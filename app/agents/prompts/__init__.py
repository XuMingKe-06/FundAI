"""
提示词模板模块

提供各智能体的提示词模板，包括：
- base.py: 提示词基类和通用模板
- fundamental.py: 基本面分析师提示词
- technical.py: 技术分析师提示词
- risk.py: 风险分析师提示词
- cost.py: 成本分析师提示词
- sentiment.py: 情绪分析师提示词
- decision.py: 决策智能体提示词
"""
from app.agents.prompts.base import (
    PromptTemplate,
    StandardOutputSchema,
    CommonTemplates,
    AnalysisDimension,
    OutputFormat
)

from app.agents.prompts.fundamental import (
    FundamentalPromptTemplate,
    FUNDAMENTAL_SYSTEM_PROMPT,
    FUNDAMENTAL_OUTPUT_SCHEMA
)

from app.agents.prompts.technical import (
    TechnicalPromptTemplate,
    TECHNICAL_SYSTEM_PROMPT,
    TECHNICAL_OUTPUT_SCHEMA
)

from app.agents.prompts.risk import (
    RiskPromptTemplate,
    RISK_SYSTEM_PROMPT,
    RISK_OUTPUT_SCHEMA
)

from app.agents.prompts.cost import (
    CostPromptTemplate,
    COST_SYSTEM_PROMPT,
    COST_OUTPUT_SCHEMA
)

from app.agents.prompts.sentiment import (
    SentimentPromptTemplate,
    SENTIMENT_SYSTEM_PROMPT,
    SENTIMENT_OUTPUT_SCHEMA
)

from app.agents.prompts.decision import (
    DecisionPromptTemplate,
    DECISION_SYSTEM_PROMPT,
    DECISION_OUTPUT_SCHEMA
)


__all__ = [
    "PromptTemplate",
    "StandardOutputSchema",
    "CommonTemplates",
    "AnalysisDimension",
    "OutputFormat",
    "FundamentalPromptTemplate",
    "FUNDAMENTAL_SYSTEM_PROMPT",
    "FUNDAMENTAL_OUTPUT_SCHEMA",
    "TechnicalPromptTemplate",
    "TECHNICAL_SYSTEM_PROMPT",
    "TECHNICAL_OUTPUT_SCHEMA",
    "RiskPromptTemplate",
    "RISK_SYSTEM_PROMPT",
    "RISK_OUTPUT_SCHEMA",
    "CostPromptTemplate",
    "COST_SYSTEM_PROMPT",
    "COST_OUTPUT_SCHEMA",
    "SentimentPromptTemplate",
    "SENTIMENT_SYSTEM_PROMPT",
    "SENTIMENT_OUTPUT_SCHEMA",
    "DecisionPromptTemplate",
    "DECISION_SYSTEM_PROMPT",
    "DECISION_OUTPUT_SCHEMA",
]


PROMPT_REGISTRY = {
    "fundamental": {
        "template": FundamentalPromptTemplate,
        "system_prompt": FUNDAMENTAL_SYSTEM_PROMPT,
        "output_schema": FUNDAMENTAL_OUTPUT_SCHEMA,
        "score_range": (1, 5)
    },
    "technical": {
        "template": TechnicalPromptTemplate,
        "system_prompt": TECHNICAL_SYSTEM_PROMPT,
        "output_schema": TECHNICAL_OUTPUT_SCHEMA,
        "score_range": (1, 5)
    },
    "risk": {
        "template": RiskPromptTemplate,
        "system_prompt": RISK_SYSTEM_PROMPT,
        "output_schema": RISK_OUTPUT_SCHEMA,
        "score_range": (1, 5)
    },
    "cost": {
        "template": CostPromptTemplate,
        "system_prompt": COST_SYSTEM_PROMPT,
        "output_schema": COST_OUTPUT_SCHEMA,
        "score_range": (1, 5)
    },
    "sentiment": {
        "template": SentimentPromptTemplate,
        "system_prompt": SENTIMENT_SYSTEM_PROMPT,
        "output_schema": SENTIMENT_OUTPUT_SCHEMA,
        "score_range": (-5, 5)
    },
    "decision": {
        "template": DecisionPromptTemplate,
        "system_prompt": DECISION_SYSTEM_PROMPT,
        "output_schema": DECISION_OUTPUT_SCHEMA,
        "score_range": (None, None)
    }
}


def get_prompt_template(agent_type: str) -> PromptTemplate:
    """
    获取指定类型的提示词模板

    Args:
        agent_type: 智能体类型

    Returns:
        对应的提示词模板实例

    Raises:
        ValueError: 如果智能体类型不存在
    """
    registry = {
        "fundamental": FundamentalPromptTemplate,
        "technical": TechnicalPromptTemplate,
        "risk": RiskPromptTemplate,
        "cost": CostPromptTemplate,
        "sentiment": SentimentPromptTemplate,
        "decision": DecisionPromptTemplate
    }

    template_class = registry.get(agent_type)
    if template_class is None:
        raise ValueError(f"未知的智能体类型: {agent_type}")

    return template_class()


def get_system_prompt(agent_type: str) -> str:
    """
    获取指定类型的系统提示词

    Args:
        agent_type: 智能体类型

    Returns:
        系统提示词字符串
    """
    return PROMPT_REGISTRY.get(agent_type, {}).get("system_prompt", "")


def get_output_schema(agent_type: str) -> dict:
    """
    获取指定类型的输出JSON Schema

    Args:
        agent_type: 智能体类型

    Returns:
        输出JSON Schema字典
    """
    return PROMPT_REGISTRY.get(agent_type, {}).get("output_schema", {})


def get_score_range(agent_type: str) -> tuple:
    """
    获取指定类型的评分范围

    Args:
        agent_type: 智能体类型

    Returns:
        评分范围元组 (min, max)
    """
    return PROMPT_REGISTRY.get(agent_type, {}).get("score_range", (1, 5))
