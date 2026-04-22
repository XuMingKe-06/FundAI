"""
基本面提示词测试
"""
import pytest
from app.agents.prompts.fundamental import FundamentalPromptTemplate


class TestFundamentalPromptTemplate:
    """FundamentalPromptTemplate测试类"""
    
    def test_fundamental_system_prompt(self):
        """测试系统提示词生成"""
        template = FundamentalPromptTemplate()
        prompt = template.get_system_prompt()
        
        assert "基本面" in prompt
        assert "基金经理" in prompt
        assert "持仓" in prompt or "业绩" in prompt
    
    def test_fundamental_user_prompt(self):
        """测试用户提示词生成"""
        template = FundamentalPromptTemplate()
        context = {
            "fund_code": "000001",
            "fund_info": {"fund_name": "测试基金"}
        }
        prompt = template.get_user_prompt(context)
        
        assert "000001" in prompt or "测试基金" in prompt
    
    def test_fundamental_output_schema(self):
        """测试输出schema"""
        template = FundamentalPromptTemplate()
        schema = template.get_output_schema()
        
        assert "score" in schema["properties"]
        assert "summary" in schema["properties"]
        assert "details" in schema["properties"]
    
    def test_fundamental_score_range(self):
        """测试评分范围"""
        template = FundamentalPromptTemplate()
        
        assert template.score_range == (1, 5)
    
    def test_fundamental_build_prompt(self):
        """测试完整提示词构建"""
        template = FundamentalPromptTemplate()
        context = {
            "fund_code": "000001",
            "fund_info": {"fund_name": "测试基金", "fund_manager": "张三"}
        }
        
        system_prompt = template.get_system_prompt()
        user_prompt = template.get_user_prompt(context)
        
        assert len(system_prompt) > 0
        assert len(user_prompt) > 0
