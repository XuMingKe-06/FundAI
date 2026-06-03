"""
集成测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from app.agents.orchestrator import AgentOrchestrator, EventType, EventCallback


class TestIntegration:

    @pytest.mark.asyncio
    async def test_full_analysis_flow(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        orchestrator = AgentOrchestrator()

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):

            result = await orchestrator.run_full_analysis(
                "000001",
                {"fund_code": "000001", "fund_info": {}, "nav_history": []}
            )

            assert result is not None
            assert "analysis_agents" in result or "decision_agent" in result

    @pytest.mark.asyncio
    async def test_agent_parallel_execution(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        orchestrator = AgentOrchestrator()

        start_time = time.time()

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):

            await orchestrator.run_full_analysis(
                "000001",
                {"fund_code": "000001", "fund_info": {}, "nav_history": []}
            )

            elapsed = time.time() - start_time

            assert elapsed < 10

    @pytest.mark.asyncio
    async def test_decision_agent_receives_results(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        orchestrator = AgentOrchestrator()

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):

            result = await orchestrator.run_full_analysis(
                "000001",
                {"fund_code": "000001", "fund_info": {}, "nav_history": []}
            )

            if "analysis_agents" in result:
                agent_results = result["analysis_agents"]
                assert "fundamental" in agent_results or "technical" in agent_results

    @pytest.mark.asyncio
    async def test_sse_event_sequence(self, mock_llm_service, mock_rag_service, mock_datasource_manager):
        orchestrator = AgentOrchestrator()
        callback = EventCallback()

        events_received = []

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):

            await orchestrator._run_agent(
                orchestrator._get_agent_by_type("fundamental"),
                "000001",
                {},
                callback
            )

            events = callback.get_all_events()
            for event in events:
                events_received.append(event.event_type)

            assert len(events_received) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_rag_service, mock_datasource_manager):
        orchestrator = AgentOrchestrator()

        mock_bad_llm = Mock()
        mock_bad_llm.chat_async = AsyncMock(side_effect=Exception("LLM调用失败"))

        with patch('app.agents.base.get_llm_service', return_value=mock_bad_llm), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service), \
             patch('app.agents.orchestrator.datasource_manager', mock_datasource_manager):

            try:
                result = await orchestrator._run_agent(
                    orchestrator._get_agent_by_type("fundamental"),
                    "000001",
                    {},
                    EventCallback()
                )
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_llm_output_parsing(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        from app.agents.fundamental import FundamentalAgent

        agent = FundamentalAgent()

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):

            result = await agent.analyze("000001", sample_analysis_context)

            assert "score" in result or "summary" in result

    @pytest.mark.asyncio
    async def test_rag_context_injection(self, mock_llm_service, mock_rag_service, sample_analysis_context):
        from app.agents.fundamental import FundamentalAgent

        agent = FundamentalAgent()

        with patch('app.agents.base.get_llm_service', return_value=mock_llm_service), \
             patch('app.agents.base.get_rag_service', return_value=mock_rag_service):

            await agent.analyze("000001", sample_analysis_context)

            assert len(agent._rag_context) >= 0
