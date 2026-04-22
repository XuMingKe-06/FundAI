"""
决策提示词测试
"""
import pytest
from app.agents.prompts.decision import DecisionPromptTemplate


class TestDecisionPromptTemplate:
    """DecisionPromptTemplate测试类"""
    
    def test_decision_system_prompt(self):
        """测试系统提示词生成"""
        template = DecisionPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "决策" in prompt or "短线" in prompt or "长线" in prompt
    
    def test_decision_output_schema(self):
        """测试输出schema"""
        template = DecisionPromptTemplate()
        schema = template.get_output_schema()
        
        assert "short_term_decision" in schema["properties"] or "details" in schema["properties"]
    
    def test_decision_no_score(self):
        """测试决策智能体无单独评分"""
        template = DecisionPromptTemplate()
        
        assert template.score_range is None or template.score_range == (None, None)
