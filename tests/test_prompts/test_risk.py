"""
风险分析提示词测试
"""
import pytest
from app.agents.prompts.risk import RiskPromptTemplate


class TestRiskPromptTemplate:
    """RiskPromptTemplate测试类"""
    
    def test_risk_system_prompt(self):
        """测试系统提示词生成"""
        template = RiskPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "风险" in prompt
        assert "波动率" in prompt or "回撤" in prompt or "夏普" in prompt
    
    def test_risk_output_schema(self):
        """测试输出schema"""
        template = RiskPromptTemplate()
        schema = template.get_output_schema()
        
        assert "score" in schema["properties"]
        assert "details" in schema["properties"]
    
    def test_risk_score_range(self):
        """测试评分范围"""
        template = RiskPromptTemplate()
        
        assert template.score_range == (1, 5)
