"""
分析任务管理器

提供智能体分析任务的后台执行、共享事件流、断线重连回放等能力。
核心目标：将分析任务的生命周期与 HTTP/SSE 连接解耦，确保：
- 页面刷新或客户端断开后，后台分析继续运行
- 新的 SSE 连接可以订阅到已有的后台任务并回放历史事件
- 同一会话不会重复启动多个分析任务
"""
import asyncio
import json
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from loguru import logger
from sqlalchemy import select

from app.agents.orchestrator import AgentOrchestrator
from app.core.database import AsyncSessionLocal
from app.models.analysis import AnalysisSession
from app.services.report_service import save_agent_outputs, save_decision_report, save_fallback_report


# 单个会话最多保留的回放事件数，防止内存无限增长
MAX_REPLAY_EVENTS_PER_SESSION = 2000
# 已完成的任务在内存中保留的秒数，供重连/查询使用
COMPLETED_TASK_TTL_SECONDS = 300


@dataclass
class AnalysisTask:
    """后台分析任务封装"""
    session_id: str
    fund_code: str
    task: asyncio.Task
    events: deque  # (seq, event_type, data)
    new_event: asyncio.Event
    status: str = "running"  # pending / running / completed / failed
    error_message: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    completed_agents: set = field(default_factory=set)
    running_agents: set = field(default_factory=set)
    next_seq: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def is_active(self) -> bool:
        """任务是否仍在运行"""
        return self.status == "running" and not self.task.done()

    @property
    def progress(self) -> int:
        """当前进度百分比（基于 5 个分析智能体 + 1 个决策智能体）"""
        total = 6
        return min(100, int(len(self.completed_agents) / total * 100))

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """记录事件并通知所有订阅者"""
        seq = self.next_seq
        self.next_seq += 1
        self.events.append((seq, event_type, data))
        self.new_event.set()


class AnalysisTaskManager:
    """
    分析任务管理器（单例）

    管理所有后台分析任务，提供：
    - start: 启动新分析任务（若已存在则返回已有任务）
    - subscribe: 订阅任务事件流（回放 + 实时）
    - get_task: 获取任务状态
    - cleanup: 清理已完成/失败任务
    """

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance._tasks: Dict[str, AnalysisTask] = {}
            cls._instance._lock = asyncio.Lock()
            cls._instance._cleanup_task: Optional[asyncio.Task] = None
        return cls._instance

    def _ensure_cleanup_loop(self) -> None:
        """确保周期性清理任务已启动"""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            except RuntimeError:
                # 当前没有事件循环时忽略，下次有连接时再启动
                pass

    async def _cleanup_loop(self) -> None:
        """每 60 秒清理一次已过期的已完成任务"""
        while True:
            try:
                await asyncio.sleep(60)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("分析任务清理循环异常 | error={}", e)

    async def _cleanup_expired(self) -> None:
        """清理超过 TTL 的已完成任务"""
        now = datetime.now(timezone.utc)
        expired_sessions = []
        async with self._lock:
            for session_id, task in self._tasks.items():
                if task.status in ("completed", "failed") and task.completed_at:
                    elapsed = (now - task.completed_at).total_seconds()
                    if elapsed > COMPLETED_TASK_TTL_SECONDS:
                        expired_sessions.append(session_id)
            for session_id in expired_sessions:
                task = self._tasks.pop(session_id, None)
                if task and not task.task.done():
                    task.task.cancel()
                logger.info("清理过期分析任务 | session_id={}", session_id)

    async def start(
        self,
        session_id: str,
        fund_code: str,
        context: Dict[str, Any],
        analysis_mode: str,
        save_func: Optional[Callable[[Any], Any]] = None,
    ) -> AnalysisTask:
        """
        启动后台分析任务

        若同 session_id 的任务已存在且未结束，则直接返回已有任务，
        避免重复执行分析。
        """
        async with self._lock:
            existing = self._tasks.get(session_id)
            if existing and existing.is_active:
                logger.info("分析任务已存在，直接复用 | session_id={}", session_id)
                return existing

            # 如果存在已完成的任务，但在 TTL 内，也直接返回，允许重连回放最后的完成事件
            if existing and existing.status in ("completed", "failed"):
                now = datetime.now(timezone.utc)
                if existing.completed_at and (now - existing.completed_at).total_seconds() <= COMPLETED_TASK_TTL_SECONDS:
                    logger.info("分析任务刚完成，复用任务对象 | session_id={} | status={}", session_id, existing.status)
                    return existing
                # 否则移除旧任务，重新启动
                self._tasks.pop(session_id, None)

        events: deque = deque(maxlen=MAX_REPLAY_EVENTS_PER_SESSION)
        new_event = asyncio.Event()
        orchestrator = AgentOrchestrator()

        analysis_task = AnalysisTask(
            session_id=session_id,
            fund_code=fund_code,
            task=None,  # type: ignore  # 先占位，随后赋值
            events=events,
            new_event=new_event,
            status="running",
        )

        task = asyncio.create_task(
            self._run_analysis(
                analysis_task=analysis_task,
                fund_code=fund_code,
                context=context,
                analysis_mode=analysis_mode,
                orchestrator=orchestrator,
                save_func=save_func,
            )
        )
        analysis_task.task = task

        async with self._lock:
            self._tasks[session_id] = analysis_task

        # 更新数据库会话状态为 running
        try:
            async with AsyncSessionLocal() as db_session:
                await self._update_session_status(db_session, session_id, "running")
        except Exception as e:
            logger.error("更新会话为运行状态失败 | session_id={} | error={}", session_id, e)

        self._ensure_cleanup_loop()
        logger.info("后台分析任务已启动 | session_id={} | fund_code={} | mode={}", session_id, fund_code, analysis_mode)
        return analysis_task

    async def _run_analysis(
        self,
        analysis_task: AnalysisTask,
        fund_code: str,
        context: Dict[str, Any],
        analysis_mode: str,
        orchestrator: AgentOrchestrator,
        save_func: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        """在后台运行完整分析流程，所有事件写入任务事件列表"""
        session_id = analysis_task.session_id

        async def emit(event_type: str, data: Dict[str, Any]) -> None:
            analysis_task.emit(event_type, data)

        async def run_single_agent(agent) -> None:
            """运行单个智能体并推送事件"""
            agent_type = agent.agent_type
            async with analysis_task.lock:
                analysis_task.running_agents.add(agent_type)

            try:
                # 绑定回调
                async def on_thinking(content: str) -> None:
                    await emit("thinking", {
                        "agent_type": agent_type,
                        "content": content,
                        "thinking_id": str(uuid.uuid4()),
                        "thinking_type": "normal",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    })

                async def on_streaming_thinking(thinking_id: str, chunk: str, thinking_type: str, is_complete: bool = False) -> None:
                    await emit("llm_thinking_stream", {
                        "agent_type": agent_type,
                        "thinking_id": thinking_id,
                        "content": chunk,
                        "thinking_type": thinking_type,
                        "is_complete": is_complete,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    })

                async def on_tool_call(tool_name: str, tool_args: Dict[str, Any], result: Optional[Dict[str, Any]] = None, status: str = "pending") -> None:
                    await emit("tool_call", {
                        "agent_type": agent_type,
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result,
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    })

                agent.set_thinking_callback(on_thinking)
                agent.set_streaming_thinking_callback(on_streaming_thinking)
                agent.set_tool_call_callback(on_tool_call)

                await emit("agent_status", {
                    "agent_type": agent_type,
                    "status": "running",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                })

                result = await agent.run(fund_code, context)
                orchestrator.agent_results[agent_type] = result

                # 保存智能体快照
                if save_func:
                    try:
                        await save_func(agent)
                    except Exception as save_err:
                        logger.warning("保存智能体 {} 快照失败 | error={}", agent_type, save_err)

                completed_data = {
                    "agent_type": agent_type,
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                if agent.score is not None:
                    completed_data["score"] = float(agent.score)
                if agent.summary:
                    completed_data["summary"] = agent.summary
                await emit("agent_complete", completed_data)

                await emit("result", {
                    "agent_type": agent_type,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                })

            except Exception as e:
                logger.error("智能体 {} 执行失败 | session_id={} | error={}", agent_type, session_id, e)
                orchestrator.agent_results[agent_type] = {
                    "agent_type": agent_type,
                    "status": "failed",
                    "error": str(e),
                }
                if save_func:
                    try:
                        await save_func(agent)
                    except Exception as save_err:
                        logger.warning("保存失败智能体 {} 快照失败 | error={}", agent_type, save_err)

                await emit("agent_complete", {
                    "agent_type": agent_type,
                    "status": "failed",
                    "score": None,
                    "summary": str(e)[:200],
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                })
                if agent_type == "decision":
                    await emit("error", {
                        "error_type": "AgentError",
                        "agent_type": agent_type,
                        "message": str(e)[:200],
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    })
            finally:
                agent.set_thinking_callback(None)
                agent.set_streaming_thinking_callback(None)
                agent.set_tool_call_callback(None)
                async with analysis_task.lock:
                    analysis_task.running_agents.discard(agent_type)
                    analysis_task.completed_agents.add(agent_type)

        try:
            # 第一阶段：分析智能体
            if analysis_mode == "sequential":
                for agent in orchestrator.analysis_agents:
                    await run_single_agent(agent)
                    context["agent_results"] = orchestrator.agent_results
            else:
                analysis_tasks = [asyncio.create_task(run_single_agent(a)) for a in orchestrator.analysis_agents]
                await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # 第二阶段：决策智能体
            context["agent_results"] = orchestrator.agent_results
            await run_single_agent(orchestrator.decision_agent)

            # 持久化：保存智能体输出和决策报告
            await self._persist_results(session_id, orchestrator)

            analysis_task.status = "completed"
            analysis_task.completed_at = datetime.now(timezone.utc)

            await emit("analysis_complete", {
                "session_id": session_id,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            })

            logger.info("后台分析任务完成 | session_id={}", session_id)

        except asyncio.CancelledError:
            logger.info("后台分析任务被取消 | session_id={}", session_id)
            analysis_task.status = "failed"
            analysis_task.error_message = "任务被取消"
            analysis_task.completed_at = datetime.now(timezone.utc)
            raise
        except Exception as e:
            logger.exception("后台分析任务异常 | session_id={} | error={}", session_id, e)
            analysis_task.status = "failed"
            analysis_task.error_message = str(e)
            analysis_task.completed_at = datetime.now(timezone.utc)
            await self._set_session_status_failed(session_id)
            await emit("error", {
                "error_type": "AnalysisError",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            })

    async def _persist_results(self, session_id: str, orchestrator: AgentOrchestrator) -> None:
        """持久化智能体输出和决策报告到数据库"""
        try:
            async with AsyncSessionLocal() as db_session:
                # 保存智能体输出
                try:
                    await save_agent_outputs(db_session, session_id, orchestrator)
                except Exception as e:
                    logger.error("保存智能体输出失败 | session_id={} | error={}", session_id, e)
                    await db_session.rollback()

                # 保存决策报告
                report_saved = False
                try:
                    await save_decision_report(db_session, session_id, orchestrator)
                    report_saved = True
                except Exception as e:
                    logger.error("保存决策报告失败 | session_id={} | error={}", session_id, e)
                    await db_session.rollback()

                # 降级报告兜底
                if not report_saved:
                    try:
                        await save_fallback_report(
                            db_session,
                            session_id,
                            orchestrator,
                            "部分数据获取失败，报告基于有限数据生成"
                        )
                    except Exception as e2:
                        logger.error("保存降级报告失败 | session_id={} | error={}", session_id, e2)
                        await db_session.rollback()

                # 更新会话状态
                await self._update_session_status(db_session, session_id, "completed")
        except Exception as e:
            logger.exception("持久化分析结果失败 | session_id={} | error={}", session_id, e)

    async def _update_session_status(
        self,
        db_session,
        session_id: str,
        status: str,
    ) -> None:
        """更新 AnalysisSession 的 status 字段"""
        try:
            result = await db_session.execute(
                select(AnalysisSession).where(AnalysisSession.id == session_id)
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.status = status
                if status in ("completed", "failed"):
                    session_obj.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db_session.commit()
                logger.info("会话状态更新 | session_id={} | status={}", session_id, status)
            else:
                logger.warning("更新会话状态失败，会话不存在 | session_id={}", session_id)
        except Exception as e:
            logger.error("更新会话状态失败 | session_id={} | status={} | error={}", session_id, status, e)
            await db_session.rollback()

    async def _set_session_status_failed(self, session_id: str) -> None:
        """将会话状态设置为失败"""
        try:
            async with AsyncSessionLocal() as db_session:
                await self._update_session_status(db_session, session_id, "failed")
        except Exception as e:
            logger.error("设置会话失败状态异常 | session_id={} | error={}", session_id, e)

    async def _get_task(self, session_id: str) -> Optional[AnalysisTask]:
        async with self._lock:
            return self._tasks.get(session_id)

    async def subscribe(
        self,
        session_id: str,
        request=None,
    ) -> AsyncGenerator[str, None]:
        """
        订阅指定会话的事件流

        先回放 events 中的历史事件，再通过 Event 等待并消费新事件。
        使用序列号避免同一事件被重复发送。
        客户端断开时仅停止生成，不会取消后台任务。
        """
        task_obj = await self._get_task(session_id)
        if task_obj is None:
            logger.warning("订阅失败，任务不存在 | session_id={}", session_id)
            return

        last_seq = -1

        # 回放已有事件
        for seq, event_type, data in list(task_obj.events):
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
            last_seq = seq

        # 实时消费新事件
        try:
            while True:
                # 如果任务已结束且已消费到最后一个事件，退出
                if task_obj.task.done() and last_seq >= task_obj.next_seq - 1:
                    logger.debug("任务已结束且事件消费完毕，结束订阅 | session_id={}", session_id)
                    break

                # 检测客户端是否已断开，若断开则优雅退出，不取消任务
                if request is not None:
                    try:
                        disconnected = await asyncio.wait_for(request.is_disconnected(), timeout=0.1)
                    except Exception:
                        disconnected = False
                    if disconnected:
                        logger.info("客户端断开，停止当前订阅但不取消后台任务 | session_id={}", session_id)
                        break

                try:
                    await asyncio.wait_for(task_obj.new_event.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                task_obj.new_event.clear()

                # 消费所有新事件
                for seq, event_type, data in list(task_obj.events):
                    if seq > last_seq:
                        yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
                        last_seq = seq

        except asyncio.CancelledError:
            logger.info("订阅生成器被取消 | session_id={}", session_id)
            # 不取消后台任务
            raise

    def get_task_sync(self, session_id: str) -> Optional[AnalysisTask]:
        """同步获取任务对象，用于不需要等待锁的场景"""
        return self._tasks.get(session_id)

    async def cleanup(self, session_id: str) -> None:
        """手动清理指定任务"""
        async with self._lock:
            task_obj = self._tasks.pop(session_id, None)
        if task_obj and not task_obj.task.done():
            task_obj.task.cancel()
            try:
                await task_obj.task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        logger.info("手动清理分析任务 | session_id={}", session_id)


# 全局任务管理器实例
analysis_task_manager = AnalysisTaskManager()
