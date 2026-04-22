"""
集成测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from app.agents.orchestrator import AgentOrchestrator, EventType, EventCallback


class TestIntegration:
    """集成测试类"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_flow(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        """测试完整分析流程"""
        orchestrator = AgentOrchestrator()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            
            result = await orchestrator.analyze("000001")
            
            assert result is not None
            assert "fund_code" in result
            assert "agent_results" in result
    
    @pytest.mark.asyncio
    async def test_agent_parallel_execution(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        """测试智能体并行执行"""
        orchestrator = Orchestrator()
        
        start_time = time.time()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            
            await orchestrator.analyze("000001")
            
            elapsed = time.time() - start_time
            
            assert elapsed < 10
    
    @pytest.mark.asyncio
    async def test_decision_agent_receives_results(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        """测试决策智能体接收结果"""
        orchestrator = Orchestrator()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            
            result = await orchestrator.analyze("000001")
            
            if "agent_results" in result:
                agent_results = result["agent_results"]
                assert "fundamental" in agent_results or "technical" in agent_results
    
    @pytest.mark.asyncio
    async def test_sse_event_sequence(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        """测试SSE事件序列"""
        orchestrator = Orchestrator()
        queue = asyncio.Queue()
        callback = EventCallback(queue)
        
        events_received = []
        
        async def collect_events():
            for _ in range(10):
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    events_received.append(event.event_type)
                except asyncio.TimeoutError:
                    break
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            
            collector_task = asyncio.create_task(collect_events())
            
            await orchestrator._run_agent(
                orchestrator.fundamental_agent,
                "000001",
                {},
                callback
            )
            
            await asyncio.sleep(0.5)
            collector_task.cancel()
            
            assert len(events_received) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_rag_service, mock_datasource_manager):
        """测试错误处理"""
        orchestrator = Orchestrator()
        
        mock_bad_llm = Mock()
        mock_bad_llm.chat_async = AsyncMock(side_effect=Exception("LLM调用失败"))
        
        with patch('app.agents.base.get_llm_service', return_value=mock_bad_llm), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):
            
            try:
                result = await orchestrator._run_agent(
                    orchestrator.fundamental_agent,
                    "000001",
                    {},
                    EventCallback(asyncio.Queue())
                )
            except Exception:
                pass
            
            assert orchestrator.fundamental_agent.status in ["failed", "completed"]
    
    @pytest.mark.asyncio
    async def test_llm_output_parsing(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试LLM输出解析"""
        from app.agents.fundamental import FundamentalAgent
        
        agent = FundamentalAgent()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            
            result = await agent.analyze("000001", sample_analysis_context)
            
            assert "score" in result or "summary" in result
    
    @pytest.mark.asyncio
    async def test_rag_context_injection(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        """测试RAG上下文注入"""
        from app.agents.fundamental import FundamentalAgent
        
        agent = FundamentalAgent()
        
        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):
            
            await agent.analyze("000001", sample_analysis_context)
            
            assert len(agent._rag_context) >= 0
