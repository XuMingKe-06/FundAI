"""
成本分析提示词测试
"""
import pytest
from app.agents.prompts.cost import CostPromptTemplate


class TestCostPromptTemplate:
    """CostPromptTemplate测试类"""
    
    def test_cost_system_prompt(self):
        """测试系统提示词生成"""
        template = CostPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "成本" in prompt or "费率" in prompt
    
    def test_cost_output_schema(self):
        """测试输出schema"""
        template = CostPromptTemplate()
        schema = template.get_output_schema()
        
        assert "score" in schema["properties"]
        assert "details" in schema["properties"]
    
    def test_cost_score_range(self):
        """测试评分范围"""
        template = CostPromptTemplate()
        
        assert template.score_range == (1, 5)
