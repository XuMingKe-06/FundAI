"""
智能体基类测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from app.agents.base import BaseAgent


class ConcreteAgent(BaseAgent):
    """具体智能体实现用于测试"""
    
    async def analyze(self, fund_code: str, context: dict) -> dict:
        await self.run_llm_analysis(fund_code, context)
        return self.to_dict()


class TestBaseAgent:
    """BaseAgent测试类"""
    
    def test_base_agent_init(self):
        """测试智能体初始化"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        
        assert agent.agent_type == "fundamental"
        assert agent.name == "测试智能体"
        assert agent.status == "pending"
        assert agent.score is None
        assert agent.summary is None
    
    @pytest.mark.asyncio
    async def test_base_agent_add_thinking(self):
        """测试添加思考过程"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        
        await agent.add_thinking("正在分析数据...")
        
        assert len(agent.thinking_process) == 1
        assert agent.thinking_process[0]["text"] == "正在分析数据..."
    
    @pytest.mark.asyncio
    async def test_base_agent_add_thinking_callback(self):
        """测试思考回调"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        
        callback_called = []
        async def callback(content):
            callback_called.append(content)
        
        agent.set_thinking_callback(callback)
        await agent.add_thinking("测试思考")
        
        assert len(callback_called) == 1
        assert callback_called[0] == "测试思考"
    
    def test_base_agent_add_tool_call(self):
        """测试添加工具调用记录"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        
        agent.add_tool_call("get_fund_info", {"fund_code": "000001"})
        
        assert len(agent.tools_called) == 1
        assert agent.tools_called[0]["name"] == "get_fund_info"
    
    def test_base_agent_get_system_prompt(self):
        """测试获取系统提示词"""
        agent = ConcreteAgent("fundamental", "基本面分析师")
        
        prompt = agent.get_system_prompt()
        
        assert len(prompt) > 0
    
    def test_base_agent_get_tools(self):
        """测试获取工具列表"""
        agent = ConcreteAgent("fundamental", "基本面分析师")
        
        tools = agent.get_tools()
        
        assert isinstance(tools, list)
    
    def test_base_agent_build_context_prompt(self):
        """测试构建上下文提示词"""
        agent = ConcreteAgent("fundamental", "基本面分析师")
        context = {"fund_code": "000001", "fund_info": {"fund_name": "测试基金"}}
        
        prompt = agent.build_context_prompt(context)
        
        assert len(prompt) > 0
    
    def test_base_agent_parse_llm_output_json(self):
        """测试解析JSON输出"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        llm_response = json.dumps({
            "score": 3.5,
            "summary": "测试摘要",
            "details": {"key": "value"}
        })
        
        result = agent.parse_llm_output(llm_response)
        
        assert agent.score == 3.5
        assert agent.summary == "测试摘要"
        assert "key" in agent.details
    
    def test_base_agent_parse_llm_output_fallback(self):
        """测试解析失败降级"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        llm_response = "这不是JSON格式的响应"
        
        result = agent.parse_llm_output(llm_response)
        
        assert result.get("parse_error") is True
    
    def test_base_agent_to_dict(self):
        """测试转换为字典"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        agent.status = "completed"
        agent.score = 3.5
        
        result = agent.to_dict()
        
        assert result["agent_type"] == "fundamental"
        assert result["name"] == "测试智能体"
        assert result["status"] == "completed"
        assert result["score"] == 3.5
    
    @pytest.mark.asyncio
    async def test_base_agent_run(self, mock_rag_service, sample_analysis_context):
        """测试运行智能体"""
        agent = ConcreteAgent("fundamental", "测试智能体")
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"score": 3.5, "summary": "测试", "details": {}}', tool_calls=None))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mock_llm_service = Mock()
        mock_llm_service.get_async_client = Mock(return_value=mock_client)
        mock_llm_service.get_model_name = Mock(return_value="test-model")
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await agent.run("000001", sample_analysis_context)
            
            assert agent.status == "completed"
            assert "agent_type" in result
