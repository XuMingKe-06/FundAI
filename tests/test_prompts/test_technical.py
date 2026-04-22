"""
技术分析提示词测试
"""
import pytest
from app.agents.prompts.technical import TechnicalPromptTemplate


class TestTechnicalPromptTemplate:
    """TechnicalPromptTemplate测试类"""
    
    def test_technical_system_prompt(self):
        """测试系统提示词生成"""
        template = TechnicalPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "技术" in prompt
        assert "MA" in prompt or "均线" in prompt or "MACD" in prompt or "RSI" in prompt
    
    def test_technical_output_schema(self):
        """测试输出schema"""
        template = TechnicalPromptTemplate()
        schema = template.get_output_schema()
        
        assert "score" in schema["properties"]
        assert "details" in schema["properties"]
    
    def test_technical_score_range(self):
        """测试评分范围"""
        template = TechnicalPromptTemplate()
        
        assert template.score_range == (1, 5)
