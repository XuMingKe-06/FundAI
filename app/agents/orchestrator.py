"""
智能体编排器
实现智能体并行调度、辩论机制、渐进式分析和 SSE 事件推送
"""
import asyncio
from loguru import logger
from typing import Dict, Any, List, Callable, Optional, AsyncGenerator, Set
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json

from app.agents.base import BaseAgent
from app.agents.fundamental import FundamentalAgent
from app.agents.technical import TechnicalAgent
from app.agents.risk import RiskAgent
from app.agents.cost import CostAgent
from app.agents.sentiment import SentimentAgent
from app.agents.decision import DecisionAgent
from app.data_sources.manager import datasource_manager
from app.core.data_quality import validate_nav_history, validate_fund_info, validate_holdings, validate_fees
from app.core.data_provenance import annotate_data_source


class EventType(Enum):
    AGENT_STATUS = "agent_status"
    THINKING = "thinking"
    LLM_THINKING_STREAM = "llm_thinking_stream"
    TOOL_CALL = "tool_call"
    AGENT_COMPLETE = "agent_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"
    DEBATE_ROUND = "debate_round"
    PROGRESSIVE_UPDATE = "progressive_update"


@dataclass
class SSEEvent:
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")

    def to_sse_message(self) -> str:
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.data, ensure_ascii=False, default=str)}\n\n"


class AgentMemory:
    """
    智能体记忆机制
    存储和检索同一基金的历史分析结果，供后续分析参考
    """

    def __init__(self, max_entries_per_fund: int = 10):
        self._memory: Dict[str, List[Dict[str, Any]]] = {}
        self._max_entries = max_entries_per_fund

    def store(self, fund_code: str, result: Dict[str, Any]) -> None:
        if fund_code not in self._memory:
            self._memory[fund_code] = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }
        self._memory[fund_code].append(entry)

        if len(self._memory[fund_code]) > self._max_entries:
            self._memory[fund_code] = self._memory[fund_code][-self._max_entries:]

    def retrieve(self, fund_code: str, limit: int = 3) -> List[Dict[str, Any]]:
        entries = self._memory.get(fund_code, [])
        return entries[-limit:]

    def get_latest(self, fund_code: str) -> Optional[Dict[str, Any]]:
        entries = self._memory.get(fund_code, [])
        return entries[-1] if entries else None

    def has_history(self, fund_code: str) -> bool:
        return fund_code in self._memory and len(self._memory[fund_code]) > 0

    def get_memory_context(self, fund_code: str) -> Dict[str, Any]:
        latest = self.get_latest(fund_code)
        if not latest:
            return {"has_history": False}

        prev_result = latest.get("result", {})
        prev_scores = {}
        for agent_type, agent_data in prev_result.get("agent_results", {}).items():
            if isinstance(agent_data, dict):
                prev_scores[agent_type] = {
                    "score": agent_data.get("score"),
                    "summary": agent_data.get("summary"),
                }

        return {
            "has_history": True,
            "last_analysis_time": latest.get("timestamp"),
            "previous_scores": prev_scores,
            "previous_decision": prev_result.get("decision", {}),
        }


agent_memory = AgentMemory()


class EventCallback:
    def __init__(self):
        self._events: List[SSEEvent] = []
        self._queue: asyncio.Queue = asyncio.Queue()

    async def emit_agent_status(
        self,
        agent_type: str,
        status: str,
        agent_name: Optional[str] = None
    ) -> None:
        event = SSEEvent(
            event_type=EventType.AGENT_STATUS,
            data={
                "agent_type": agent_type,
                "agent_name": agent_name or agent_type,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_thinking(
        self,
        agent_type: str,
        content: str
    ) -> None:
        event = SSEEvent(
            event_type=EventType.THINKING,
            data={
                "agent_type": agent_type,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_llm_thinking_stream(
        self,
        agent_type: str,
        thinking_id: str,
        content: str,
        thinking_type: str = "normal",
        is_complete: bool = False
    ) -> None:
        event = SSEEvent(
            event_type=EventType.LLM_THINKING_STREAM,
            data={
                "agent_type": agent_type,
                "thinking_id": thinking_id,
                "content": content,
                "thinking_type": thinking_type,
                "is_complete": is_complete,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_tool_call(
        self,
        agent_type: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        status: str = "pending"
    ) -> None:
        event = SSEEvent(
            event_type=EventType.TOOL_CALL,
            data={
                "agent_type": agent_type,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "result": result,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_agent_complete(
        self,
        agent_type: str,
        score: Optional[float],
        summary: Optional[str],
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        event = SSEEvent(
            event_type=EventType.AGENT_COMPLETE,
            data={
                "agent_type": agent_type,
                "status": "completed",
                "score": score,
                "summary": summary,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_analysis_complete(
        self,
        session_id: str,
        final_result: Optional[Dict[str, Any]] = None
    ) -> None:
        event = SSEEvent(
            event_type=EventType.ANALYSIS_COMPLETE,
            data={
                "session_id": session_id,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "result_summary": final_result
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_error(
        self,
        error_type: str,
        message: str,
        agent_type: Optional[str] = None
    ) -> None:
        event = SSEEvent(
            event_type=EventType.ERROR,
            data={
                "error_type": error_type,
                "message": message,
                "agent_type": agent_type,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_debate_round(
        self,
        round_num: int,
        disagreements: List[Dict[str, Any]],
        resolutions: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        event = SSEEvent(
            event_type=EventType.DEBATE_ROUND,
            data={
                "round": round_num,
                "disagreements": disagreements,
                "resolutions": resolutions,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def emit_progressive_update(
        self,
        completed_agents: List[str],
        pending_agents: List[str],
        current_results: Dict[str, Any]
    ) -> None:
        event = SSEEvent(
            event_type=EventType.PROGRESSIVE_UPDATE,
            data={
                "completed_agents": completed_agents,
                "pending_agents": pending_agents,
                "current_results": current_results,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)

    async def get_event(self) -> Optional[SSEEvent]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    def get_all_events(self) -> List[SSEEvent]:
        return self._events.copy()


class AgentOrchestrator:
    """
    智能体编排器

    负责协调多个智能体的并行执行和结果汇总，
    支持辩论机制、渐进式分析、记忆机制和 SSE 事件推送。
    """

    AGENT_TIMEOUT_SECONDS = 120
    DEBATE_MAX_ROUNDS = 2
    DEBATE_SCORE_THRESHOLD = 1.5

    ANALYSIS_AGENTS_CONFIG = [
        ("fundamental", "基本面分析师", FundamentalAgent),
        ("technical", "技术分析师", TechnicalAgent),
        ("risk", "风险分析师", RiskAgent),
        ("cost", "成本分析师", CostAgent),
        ("sentiment", "情绪分析师", SentimentAgent),
    ]

    def __init__(self):
        self.analysis_agents: List[BaseAgent] = []
        self.decision_agent: Optional[DecisionAgent] = None
        self.agent_results: Dict[str, Any] = {}
        self._agent_map: Dict[str, BaseAgent] = {}
        self._completed_agents: Set[str] = set()
        self._initialize_agents()

    def _initialize_agents(self) -> None:
        for agent_type, agent_name, agent_class in self.ANALYSIS_AGENTS_CONFIG:
            agent = agent_class()
            self.analysis_agents.append(agent)
            self._agent_map[agent_type] = agent

        self.decision_agent = DecisionAgent()
        self._agent_map["decision"] = self.decision_agent
        logger.info(f"智能体初始化完成: {len(self.analysis_agents)} 个分析智能体, 1 个决策智能体")

    def _get_agent_by_type(self, agent_type: str) -> Optional[BaseAgent]:
        return self._agent_map.get(agent_type)

    async def _build_context(self, fund_code: str) -> Dict[str, Any]:
        normalized_code = fund_code
        if '.' not in fund_code:
            normalized_code = f"{fund_code}.OF"

        logger.info("构建分析上下文 | fund_code={} | normalized_code={}", fund_code, normalized_code)

        context: Dict[str, Any] = {
            "fund_code": fund_code,
            "normalized_code": normalized_code,
            "build_time": datetime.now(timezone.utc).isoformat(),
            "data_source": {},
            "data_status": {}
        }

        try:
            fund_info = await datasource_manager.get_fund_info(normalized_code)
            if fund_info:
                context["fund_info"] = fund_info
                context["fund_name"] = fund_info.get("fund_name", "未知")
                context["fund_type"] = fund_info.get("fund_type", "未知")
                context["fund_scale"] = fund_info.get("scale") or fund_info.get("current_scale", 0)
                context["establish_date"] = fund_info.get("establish_date")
                context["fund_manager"] = fund_info.get("fund_manager", "未知")
                context["data_status"]["fund_info"] = "success"
            else:
                fund_info = await datasource_manager.get_fund_info(fund_code)
                if fund_info:
                    context["fund_info"] = fund_info
                    context["fund_name"] = fund_info.get("fund_name", "未知")
                    context["fund_type"] = fund_info.get("fund_type", "未知")
                    context["fund_scale"] = fund_info.get("scale") or fund_info.get("current_scale", 0)
                    context["establish_date"] = fund_info.get("establish_date")
                    context["fund_manager"] = fund_info.get("fund_manager", "未知")
                    context["data_status"]["fund_info"] = "success"
                else:
                    context["fund_info"] = {}
                    context["fund_name"] = "未知"
                    context["data_status"]["fund_info"] = "not_found"
        except Exception as e:
            logger.error("获取基金信息失败 | fund_code={} | error={}", normalized_code, e)
            context["fund_info"] = {}
            context["fund_name"] = "未知"
            context["data_status"]["fund_info"] = f"error: {str(e)}"

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=365 * 3)
            nav_history = await datasource_manager.get_nav_history(
                normalized_code, start_date, end_date
            )
            if nav_history and len(nav_history) > 0:
                context["nav_history"] = nav_history
                context["nav_count"] = len(nav_history)
                latest_nav = nav_history[-1] if nav_history else {}
                context["current_nav"] = latest_nav.get("nav")
                context["nav_date"] = latest_nav.get("trade_date") or latest_nav.get("date")
                context["data_status"]["nav_history"] = "success"
            else:
                nav_history = await datasource_manager.get_nav_history(
                    fund_code, start_date, end_date
                )
                if nav_history and len(nav_history) > 0:
                    context["nav_history"] = nav_history
                    context["nav_count"] = len(nav_history)
                    latest_nav = nav_history[-1] if nav_history else {}
                    context["current_nav"] = latest_nav.get("nav")
                    context["nav_date"] = latest_nav.get("trade_date") or latest_nav.get("date")
                    context["data_status"]["nav_history"] = "success"
                else:
                    context["nav_history"] = []
                    context["nav_count"] = 0
                    context["data_status"]["nav_history"] = "not_found"
        except Exception as e:
            logger.error("获取净值历史失败 | fund_code={} | error={}", normalized_code, e)
            context["nav_history"] = []
            context["nav_count"] = 0
            context["data_status"]["nav_history"] = f"error: {str(e)}"

        try:
            holdings = await datasource_manager.get_holdings(normalized_code)
            if holdings:
                context["holdings"] = holdings
                context["data_status"]["holdings"] = "success"
            else:
                holdings = await datasource_manager.get_holdings(fund_code)
                if holdings:
                    context["holdings"] = holdings
                    context["data_status"]["holdings"] = "success"
                else:
                    context["holdings"] = {}
                    context["data_status"]["holdings"] = "not_found"
        except Exception as e:
            logger.error("获取持仓信息失败 | fund_code={} | error={}", normalized_code, e)
            context["holdings"] = {}
            context["data_status"]["holdings"] = f"error: {str(e)}"

        try:
            fees = await datasource_manager.get_fund_fees(normalized_code)
            if fees:
                context["fees"] = fees
                context["data_status"]["fees"] = "success"
            else:
                fees = await datasource_manager.get_fund_fees(fund_code)
                if fees:
                    context["fees"] = fees
                    context["data_status"]["fees"] = "success"
                else:
                    context["fees"] = {}
                    context["data_status"]["fees"] = "not_found"
        except Exception as e:
            logger.error("获取费率信息失败 | fund_code={} | error={}", normalized_code, e)
            context["fees"] = {}
            context["data_status"]["fees"] = f"error: {str(e)}"

        try:
            manager_info = await datasource_manager.get_fund_manager(normalized_code)
            if manager_info:
                context["manager_info"] = manager_info
                context["data_status"]["manager_info"] = "success"
            else:
                manager_info = await datasource_manager.get_fund_manager(fund_code)
                if manager_info:
                    context["manager_info"] = manager_info
                    context["data_status"]["manager_info"] = "success"
                else:
                    context["manager_info"] = {}
                    context["data_status"]["manager_info"] = "not_found"
        except Exception as e:
            logger.error("获取基金经理信息失败 | fund_code={} | error={}", normalized_code, e)
            context["manager_info"] = {}
            context["data_status"]["manager_info"] = f"error: {str(e)}"

        nav_history = context.get("nav_history", [])
        if nav_history:
            quality_report = validate_nav_history(nav_history)
            if quality_report.has_warnings:
                for w in quality_report.warnings:
                    logger.warning(f"净值数据质量警告: {w['message']}")

        fund_info = context.get("fund_info", {})
        holdings = context.get("holdings", {})
        fees = context.get("fees", {})
        manager_info = context.get("manager_info", {})

        if fund_info:
            fund_info = annotate_data_source(fund_info, "fund_info")
            context["fund_info"] = fund_info
        if nav_history:
            nav_history_annotated = {"records": nav_history, "count": len(nav_history)}
            annotate_data_source(nav_history_annotated, "nav_history")
            nav_history = nav_history_annotated
        if holdings:
            holdings = annotate_data_source(holdings, "holdings")
            context["holdings"] = holdings
        if fees:
            fees = annotate_data_source(fees, "fees")
            context["fees"] = fees
        if manager_info:
            manager_info = annotate_data_source(manager_info, "fund_manager")
            context["manager_info"] = manager_info

        memory_context = agent_memory.get_memory_context(fund_code)
        if memory_context.get("has_history"):
            context["memory"] = memory_context
            logger.info(f"加载历史分析记忆: {fund_code}")

        context["shared_data"] = {
            "nav_history_3y": nav_history,
            "fund_info": fund_info,
            "holdings": holdings,
            "fees": fees,
            "fund_manager": manager_info,
        }

        data_summary = {k: v for k, v in context["data_status"].items()}
        logger.info("数据获取摘要 | fund_code={} | status={}", fund_code, data_summary)

        return context

    async def _run_agent(
        self,
        agent: BaseAgent,
        fund_code: str,
        context: Dict[str, Any],
        event_callback: EventCallback
    ) -> Dict[str, Any]:
        agent_type = agent.agent_type
        agent_name = agent.name

        await event_callback.emit_agent_status(agent_type, "running", agent_name)

        async def thinking_callback(content: str) -> None:
            await event_callback.emit_thinking(agent_type, content)

        async def streaming_thinking_callback(thinking_id: str, chunk_content: str, thinking_type: str, is_complete: bool = False) -> None:
            await event_callback.emit_llm_thinking_stream(
                agent_type=agent_type,
                thinking_id=thinking_id,
                content=chunk_content,
                thinking_type=thinking_type,
                is_complete=is_complete
            )

        async def tool_call_callback(
            tool_name: str,
            tool_args: Dict[str, Any],
            result: Optional[Dict[str, Any]] = None,
            status: str = "pending"
        ) -> None:
            await event_callback.emit_tool_call(
                agent_type=agent_type,
                tool_name=tool_name,
                tool_args=tool_args,
                result=result,
                status=status
            )

        agent.set_thinking_callback(thinking_callback)

        if hasattr(agent, 'set_streaming_thinking_callback'):
            agent.set_streaming_thinking_callback(streaming_thinking_callback)

        if hasattr(agent, 'set_tool_call_callback'):
            agent.set_tool_call_callback(tool_call_callback)

        try:
            result = await asyncio.wait_for(
                agent.run(fund_code, context),
                timeout=self.AGENT_TIMEOUT_SECONDS
            )

            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=agent.score,
                summary=agent.summary,
                details=agent.details
            )

            logger.debug("智能体执行完成 | agent={} | score={} | duration_ms={}", agent_name, agent.score, agent.duration_ms)

            return result

        except asyncio.TimeoutError:
            error_msg = f"智能体 {agent_name} 执行超时（超过 {self.AGENT_TIMEOUT_SECONDS} 秒）"
            logger.error("智能体执行超时 | agent={} | timeout={}s", agent_name, self.AGENT_TIMEOUT_SECONDS)

            await event_callback.emit_error(
                error_type="TimeoutError",
                message=error_msg,
                agent_type=agent_type
            )

            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=None,
                summary=f"执行超时",
                details={"error": error_msg}
            )

            return {
                "agent_type": agent_type,
                "status": "timeout",
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"智能体 {agent_name} 执行失败: {str(e)}"
            logger.exception("智能体执行失败 | agent={} | error={}", agent_name, str(e))

            await event_callback.emit_error(
                error_type=type(e).__name__,
                message=error_msg,
                agent_type=agent_type
            )

            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=None,
                summary=f"执行失败",
                details={"error": str(e)}
            )

            return {
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e)
            }

        finally:
            agent.set_thinking_callback(None)
            if hasattr(agent, 'set_tool_call_callback'):
                agent.set_tool_call_callback(None)

    def _detect_disagreements(self) -> List[Dict[str, Any]]:
        """
        检测智能体之间的评分分歧

        当两个相关维度的评分差距超过阈值时，标记为分歧
        """
        disagreements = []

        scores = {}
        for agent_type, result in self.agent_results.items():
            if isinstance(result, dict):
                score = result.get("score")
                if score is not None and isinstance(score, (int, float)):
                    scores[agent_type] = float(score)

        if len(scores) < 2:
            return disagreements

        conflict_pairs = [
            ("technical", "risk", "技术面看多但风险面评分低"),
            ("fundamental", "sentiment", "基本面良好但市场情绪低迷"),
            ("technical", "sentiment", "技术面与市场情绪方向不一致"),
            ("cost", "risk", "成本可行但风险较高"),
        ]

        for agent_a, agent_b, description in conflict_pairs:
            score_a = scores.get(agent_a)
            score_b = scores.get(agent_b)

            if score_a is not None and score_b is not None:
                diff = abs(score_a - score_b)
                if diff > self.DEBATE_SCORE_THRESHOLD:
                    disagreements.append({
                        "agents": [agent_a, agent_b],
                        "scores": {agent_a: score_a, agent_b: score_b},
                        "difference": round(diff, 2),
                        "description": description
                    })

        return disagreements

    async def _run_debate_round(
        self,
        fund_code: str,
        context: Dict[str, Any],
        disagreements: List[Dict[str, Any]],
        event_callback: EventCallback,
        round_num: int
    ) -> List[Dict[str, Any]]:
        """
        执行一轮辩论

        让分歧双方的智能体重新审视对方的分析结果，
        调整自己的评分或提供更详细的理由
        """
        await event_callback.emit_debate_round(
            round_num=round_num,
            disagreements=disagreements
        )

        resolutions = []

        for disagreement in disagreements:
            agents_involved = disagreement["agents"]
            agent_a_type = agents_involved[0]
            agent_b_type = agents_involved[1]

            agent_a = self._get_agent_by_type(agent_a_type)
            agent_b = self._get_agent_by_type(agent_b_type)

            if not agent_a or not agent_b:
                continue

            result_a = self.agent_results.get(agent_a_type, {})
            result_b = self.agent_results.get(agent_b_type, {})

            debate_context = {
                **context,
                "debate_mode": True,
                "debate_round": round_num,
                "opposing_view": {
                    "agent_type": agent_b_type,
                    "score": result_b.get("score"),
                    "summary": result_b.get("summary"),
                    "details": result_b.get("details", {}),
                },
                "own_previous_result": {
                    "score": result_a.get("score"),
                    "summary": result_a.get("summary"),
                },
                "disagreement_description": disagreement["description"],
            }

            try:
                await event_callback.emit_thinking(
                    agent_a_type,
                    f"辩论第{round_num}轮: 审视{agent_b_type}的相反观点 - {disagreement['description']}"
                )

                new_result = await self._run_agent(
                    agent_a, fund_code, debate_context, event_callback
                )

                new_score = new_result.get("score")
                old_score = result_a.get("score")

                resolution = {
                    "agent": agent_a_type,
                    "old_score": old_score,
                    "new_score": new_score,
                    "adjusted": new_score != old_score,
                    "disagreement": disagreement["description"],
                }

                if new_score is not None:
                    self.agent_results[agent_a_type] = new_result

                resolutions.append(resolution)

            except Exception as e:
                logger.error("辩论轮次异常 | round={} | error={}", round_num, e)
                resolutions.append({
                    "agent": agent_a_type,
                    "error": str(e),
                    "adjusted": False,
                })

        await event_callback.emit_debate_round(
            round_num=round_num,
            disagreements=disagreements,
            resolutions=resolutions
        )

        return resolutions

    async def run_analysis(
        self,
        session_id: str,
        fund_code: str,
        user_preference: str = "neutral",
        analysis_mode: str = "parallel",
        enable_debate: bool = True
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        执行完整分析流程

        三阶段执行：
        1. 第一阶段：并行或串行执行五个分析智能体
        2. 第二阶段（可选）：辩论机制，检测分歧并让智能体互相审视
        3. 第三阶段：执行决策智能体

        Args:
            session_id: 会话ID
            fund_code: 基金代码
            user_preference: 用户风险偏好
            analysis_mode: 分析模式（parallel/sequential）
            enable_debate: 是否启用辩论机制
        """
        event_callback = EventCallback()
        self.agent_results = {}
        self._completed_agents = set()

        async def event_producer():
            while True:
                event = await event_callback.get_event()
                if event:
                    yield event

        producer_gen = event_producer()

        async def run_analysis_task():
            try:
                context = await self._build_context(fund_code)
                context["user_preference"] = user_preference
                context["session_id"] = session_id
                context["analysis_mode"] = analysis_mode

                if analysis_mode == "sequential":
                    logger.info("开始串行执行分析智能体 | session_id={}", session_id)
                    for agent in self.analysis_agents:
                        result = await self._run_agent(agent, fund_code, context, event_callback)
                        if isinstance(result, Exception):
                            self.agent_results[agent.agent_type] = {
                                "agent_type": agent.agent_type,
                                "status": "failed",
                                "error": str(result)
                            }
                        else:
                            self.agent_results[agent.agent_type] = result
                        self._completed_agents.add(agent.agent_type)
                        context["agent_results"] = self.agent_results

                        await event_callback.emit_progressive_update(
                            completed_agents=list(self._completed_agents),
                            pending_agents=[a.agent_type for a in self.analysis_agents if a.agent_type not in self._completed_agents],
                            current_results={k: {"score": v.get("score"), "summary": v.get("summary")} for k, v in self.agent_results.items()}
                        )
                else:
                    logger.info("开始并行执行分析智能体 | session_id={}", session_id)

                    analysis_tasks = [
                        self._run_agent(agent, fund_code, context, event_callback)
                        for agent in self.analysis_agents
                    ]

                    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        agent_type = self.analysis_agents[i].agent_type
                        if isinstance(result, Exception):
                            self.agent_results[agent_type] = {
                                "agent_type": agent_type,
                                "status": "failed",
                                "error": str(result)
                            }
                        else:
                            self.agent_results[agent_type] = result
                        self._completed_agents.add(agent_type)

                logger.info("所有分析智能体执行完成 | session_id={}", session_id)

                if enable_debate:
                    disagreements = self._detect_disagreements()
                    if disagreements:
                        logger.info("检测到评分分歧，启动辩论机制 | 分歧数={}", len(disagreements))
                        for round_num in range(1, self.DEBATE_MAX_ROUNDS + 1):
                            await self._run_debate_round(
                                fund_code, context, disagreements, event_callback, round_num
                            )
                            new_disagreements = self._detect_disagreements()
                            if not new_disagreements:
                                logger.info("辩论轮次完成 | round={} | 结果=分歧已解决", round_num)
                                break
                            if len(new_disagreements) < len(disagreements):
                                disagreements = new_disagreements
                                logger.info("辩论轮次完成 | round={} | 结果=分歧减少 | 剩余={}", round_num, len(disagreements))
                            else:
                                logger.info("辩论轮次完成 | round={} | 结果=分歧未减少，停止辩论", round_num)
                                break
                    else:
                        logger.info("未检测到评分分歧，跳过辩论阶段")

                decision_context = context.copy()
                decision_context["agent_results"] = self.agent_results

                logger.info("开始执行决策智能体 | session_id={}", session_id)

                decision_result = await self._run_agent(
                    self.decision_agent,
                    fund_code,
                    decision_context,
                    event_callback
                )

                self.agent_results["decision"] = decision_result

                final_result = {
                    "session_id": session_id,
                    "fund_code": fund_code,
                    "user_preference": user_preference,
                    "agent_results": {
                        k: {
                            "score": v.get("score"),
                            "summary": v.get("summary"),
                            "status": v.get("status", "completed")
                        }
                        for k, v in self.agent_results.items()
                    },
                    "decision": decision_result.get("details", {}),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }

                agent_memory.store(fund_code, final_result)

                await event_callback.emit_analysis_complete(session_id, final_result)

            except Exception as e:
                logger.exception("分析流程异常 | session_id={} | error={}", session_id, e)
                await event_callback.emit_error(
                    error_type="AnalysisError",
                    message=str(e)
                )

        analysis_task = asyncio.create_task(run_analysis_task())

        completed = False

        while not completed:
            if analysis_task.done():
                completed = True

            async for event in producer_gen:
                yield event

            if not completed:
                await asyncio.sleep(0.05)

        try:
            await analysis_task
        except Exception as e:
            logger.exception("分析任务异常 | error={}", e)

        remaining_events = event_callback.get_all_events()
        for event in remaining_events:
            if event not in [e async for e in producer_gen]:
                yield event

    async def run_analysis_agents(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        analysis_mode: str = "parallel"
    ) -> Dict[str, Any]:
        event_callback = EventCallback()

        async def run_agent(agent: BaseAgent):
            try:
                if progress_callback:
                    await progress_callback(agent.agent_type, "running", None, None)

                result = await self._run_agent(agent, fund_code, context, event_callback)

                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "completed",
                        agent.score,
                        agent.summary
                    )

                return agent.agent_type, result
            except Exception as e:
                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "failed",
                        None,
                        str(e)
                    )
                return agent.agent_type, {"error": str(e)}

        if analysis_mode == "sequential":
            for agent in self.analysis_agents:
                agent_type, result = await run_agent(agent)
                self.agent_results[agent_type] = result
                context["agent_results"] = self.agent_results
        else:
            tasks = [run_agent(agent) for agent in self.analysis_agents]
            results = await asyncio.gather(*tasks)

            for agent_type, result in results:
                self.agent_results[agent_type] = result

        return self.agent_results

    async def run_decision_agent(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        event_callback = EventCallback()

        try:
            if progress_callback:
                await progress_callback("decision", "running", None, None)

            context["agent_results"] = self.agent_results

            result = await self._run_agent(
                self.decision_agent, fund_code, context, event_callback
            )

            if progress_callback:
                await progress_callback(
                    "decision",
                    "completed",
                    None,
                    self.decision_agent.summary
                )

            return result
        except Exception as e:
            if progress_callback:
                await progress_callback("decision", "failed", None, str(e))
            return {"error": str(e)}

    async def run_full_analysis(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        await self.run_analysis_agents(fund_code, context, progress_callback)

        decision_result = await self.run_decision_agent(fund_code, context, progress_callback)

        return {
            "analysis_agents": self.agent_results,
            "decision_agent": decision_result,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

    def get_agent_thinking_process(self, agent_type: str) -> List[Dict[str, str]]:
        if agent_type in self.agent_results:
            return self.agent_results[agent_type].get("thinking_process", [])
        if agent_type == "decision" and self.decision_agent:
            return self.decision_agent.thinking_process
        return []

    def get_agent_result(self, agent_type: str) -> Optional[Dict[str, Any]]:
        return self.agent_results.get(agent_type)

    def get_all_results(self) -> Dict[str, Any]:
        return self.agent_results.copy()
