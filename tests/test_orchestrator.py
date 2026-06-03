"""
编排器测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.agents.orchestrator import (
    AgentOrchestrator,
    EventType,
    SSEEvent,
    EventCallback
)


class TestEventType:
    """EventType测试类"""
    
    def test_event_type_enum(self):
        assert EventType.AGENT_STATUS.value == "agent_status"
        assert EventType.THINKING.value == "thinking"
        assert EventType.TOOL_CALL.value == "tool_call"
        assert EventType.AGENT_COMPLETE.value == "agent_complete"
        assert EventType.ANALYSIS_COMPLETE.value == "analysis_complete"
        assert EventType.ERROR.value == "error"
        assert EventType.DEBATE_ROUND.value == "debate_round"
        assert EventType.PROGRESSIVE_UPDATE.value == "progressive_update"


class TestSSEEvent:
    """SSEEvent测试类"""
    
    def test_sse_event_to_sse_message(self):
        """测试SSE消息转换"""
        event = SSEEvent(
            event_type=EventType.THINKING,
            data={"content": "测试思考"}
        )
        
        message = event.to_sse_message()
        
        assert "event: thinking" in message
        assert "data:" in message


class TestEventCallback:
    """EventCallback测试类"""
    
    def test_event_callback_init(self):
        """测试初始化"""
        callback = EventCallback()
        
        assert callback._events == []
        assert callback._queue is not None
    
    @pytest.mark.asyncio
    async def test_event_callback_emit_agent_status(self):
        """测试状态事件发送"""
        callback = EventCallback()
        
        await callback.emit_agent_status("fundamental", "running")
        
        assert len(callback._events) == 1
        assert callback._events[0].event_type == EventType.AGENT_STATUS
    
    @pytest.mark.asyncio
    async def test_event_callback_emit_thinking(self):
        """测试思考事件发送"""
        callback = EventCallback()
        
        await callback.emit_thinking("fundamental", "正在分析...")
        
        assert len(callback._events) == 1
        assert callback._events[0].event_type == EventType.THINKING
    
    @pytest.mark.asyncio
    async def test_event_callback_emit_tool_call(self):
        """测试工具调用事件发送"""
        callback = EventCallback()
        
        await callback.emit_tool_call(
            "fundamental",
            "get_fund_info",
            {"fund_code": "000001"},
            status="pending"
        )
        
        assert len(callback._events) == 1
        assert callback._events[0].event_type == EventType.TOOL_CALL
    
    @pytest.mark.asyncio
    async def test_event_callback_emit_agent_complete(self):
        """测试完成事件发送"""
        callback = EventCallback()
        
        await callback.emit_agent_complete("fundamental", 3.5, "测试摘要", {"key": "value"})
        
        assert len(callback._events) == 1
        assert callback._events[0].event_type == EventType.AGENT_COMPLETE


class TestAgentOrchestrator:
    """AgentOrchestrator测试类"""
    
    def test_orchestrator_init(self):
        orchestrator = AgentOrchestrator()

        assert orchestrator._get_agent_by_type("fundamental") is not None
        assert orchestrator._get_agent_by_type("technical") is not None
        assert orchestrator._get_agent_by_type("risk") is not None
        assert orchestrator._get_agent_by_type("cost") is not None
        assert orchestrator._get_agent_by_type("sentiment") is not None
        assert orchestrator.decision_agent is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_build_context(self, mock_datasource_manager, sample_fund_info):
        """测试上下文构建"""
        orchestrator = AgentOrchestrator()
        
        with patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            context = await orchestrator._build_context("000001")
            
            assert "fund_code" in context
            assert context["fund_code"] == "000001"
    
    @pytest.mark.asyncio
    async def test_orchestrator_run_agent(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试智能体执行"""
        orchestrator = AgentOrchestrator()
        callback = EventCallback()
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"score": 3.5, "summary": "测试", "details": {}}', tool_calls=None))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_llm_service.get_async_client = Mock(return_value=mock_client)
        mock_llm_service.get_model_name = Mock(return_value="test-model")
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            result = await orchestrator._run_agent(
                orchestrator._get_agent_by_type("fundamental"),
                "000001",
                sample_analysis_context,
                callback
            )
            
            assert result is not None
            assert "agent_type" in result
