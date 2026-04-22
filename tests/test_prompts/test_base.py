"""
提示词基类测试
"""
import pytest
from app.agents.prompts import get_prompt_template, get_system_prompt, get_output_schema


class TestPromptFunctions:
    """提示词函数测试类"""
    
    def test_get_prompt_template_fundamental(self):
        """测试获取基本面提示词模板"""
        template = get_prompt_template("fundamental")
        
        assert template is not None
        assert template.agent_type == "fundamental"
    
    def test_get_prompt_template_technical(self):
        """测试获取技术分析提示词模板"""
        template = get_prompt_template("technical")
        
        assert template is not None
        assert template.agent_type == "technical"
    
    def test_get_prompt_template_invalid(self):
        """测试获取无效类型提示词"""
        with pytest.raises(ValueError):
            get_prompt_template("invalid_type")
    
    def test_get_system_prompt(self):
        """测试获取系统提示词"""
        prompt = get_system_prompt("fundamental")
        
        assert prompt is not None
        assert len(prompt) > 0
        assert "基本面" in prompt or "基金经理" in prompt
    
    def test_get_output_schema(self):
        """测试获取输出schema"""
        schema = get_output_schema("fundamental")
        
        assert schema is not None
        assert "properties" in schema
        assert "score" in schema["properties"]
