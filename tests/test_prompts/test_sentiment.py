"""
情绪分析提示词测试
"""
import pytest
from app.agents.prompts.sentiment import SentimentPromptTemplate


class TestSentimentPromptTemplate:
    """SentimentPromptTemplate测试类"""
    
    def test_sentiment_system_prompt(self):
        """测试系统提示词生成"""
        template = SentimentPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "情绪" in prompt or "舆情" in prompt
    
    def test_sentiment_output_schema(self):
        """测试输出schema"""
        template = SentimentPromptTemplate()
        schema = template.get_output_schema()
        
        assert "score" in schema["properties"]
        assert "details" in schema["properties"]
    
    def test_sentiment_score_range(self):
        """测试评分范围"""
        template = SentimentPromptTemplate()
        
        assert template.score_range == (-5, 5)
