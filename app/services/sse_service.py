"""
SSE 流式推送服务
管理分析过程中的事件队列、缓冲区和流式输出
"""
import json
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Callable

from fastapi import Request

from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

# 正在分析中的会话集合（用于防止同一会话的并发编排器）
_active_analysis_sessions: set = set()
_active_analysis_lock = asyncio.Lock()

# 全局事件队列字典 -- 用于页面刷新重连时复用已有分析流
_active_event_queues: dict = {}  # key: session_id, value: asyncio.Queue
_active_queues_lock = asyncio.Lock()

# 全局事件缓冲区 -- 用于页面刷新重连时回放运行中智能体的历史事件
_active_event_buffers: dict[str, list] = {}  # key: session_id, value: list of (event_type, data)

# 全局运行中智能体追踪 -- 用于重连时发送 agent_status 事件
_active_running_agents: dict[str, set[str]] = {}  # key: session_id, value: set of agent_type


async def run_analysis_with_streaming(
    orchestrator: AgentOrchestrator,
    fund_code: str,
    context: dict,
    request: Request,
    analysis_mode: str = "parallel",
    save_func: Optional[Callable] = None,
    session_id: str = ""
):
    """
    运行分析并实时流式输出事件

    使用共享的 asyncio.Queue 桥接 agent 内部回调与 SSE 事件流：
    - agent 内部的 thinking/streaming/tool_call 回调将事件推入队列
    - 异步生成器从队列实时取出事件并 yield 给 StreamingResponse
    - parallel 模式：所有分析 agent 通过 asyncio.create_task() 并发执行
    - sequential 模式：分析 agent 按顺序逐个执行，前序结果注入后续 context
    - 事件同时写入缓冲区，支持页面刷新重连时回放运行中智能体的历史事件
    """
    event_queue: asyncio.Queue = asyncio.Queue()

    # 注册全局事件队列和缓冲区，支持页面刷新重连时复用
    if session_id:
        async with _active_queues_lock:
            _active_event_queues[session_id] = event_queue
        _active_event_buffers[session_id] = []
        _active_running_agents[session_id] = set()

    async def _emit_event(event_type: str, data: dict):
        """将事件放入队列并缓冲（用于重连回放），同时追踪运行中智能体"""
        await event_queue.put((event_type, data))
        # 缓冲非内部信号的事件
        if session_id and event_type not in ("_agent_done", "_analysis_done"):
            _active_event_buffers[session_id].append((event_type, data))
        # 追踪运行中智能体
        if session_id:
            if event_type == "agent_status" and isinstance(data, dict) and data.get("status") == "running":
                _active_running_agents[session_id].add(data.get("agent_type"))
            elif event_type == "agent_complete" and isinstance(data, dict):
                _active_running_agents[session_id].discard(data.get("agent_type"))

    async def run_single_agent(agent):
        """在后台运行单个 agent，通过共享队列实时推送事件"""
        agent_type = agent.agent_type

        # 绑定 thinking 回调
        async def on_thinking(content):
            await _emit_event("thinking", {
                "agent_type": agent_type,
                "content": content,
                "thinking_id": str(uuid.uuid4()),
                "thinking_type": "normal",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            })

        # 绑定流式 thinking 回调
        async def on_streaming_thinking(thinking_id, chunk_content, thinking_type, is_complete=False):
            await _emit_event("llm_thinking_stream", {
                "agent_type": agent_type,
                "thinking_id": thinking_id,
                "content": chunk_content,
                "thinking_type": thinking_type,
                "is_complete": is_complete,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            })

        # 绑定工具调用回调
        async def on_tool_call(tool_name, tool_args, result, status):
            await _emit_event("tool_call", {
                "agent_type": agent_type,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "result": result,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            })

        agent.set_thinking_callback(on_thinking)
        agent.set_streaming_thinking_callback(on_streaming_thinking)
        agent.set_tool_call_callback(on_tool_call)

        # 推送 running 状态
        await _emit_event("agent_status", {
            "agent_type": agent_type,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        })

        try:
            result = await agent.run(fund_code, context)
            orchestrator.agent_results[agent_type] = result

            # 保存已完成的智能体输出（支持页面刷新恢复）
            if save_func:
                try:
                    await save_func(agent)
                except Exception as save_err:
                    logger.warning(f"保存智能体 {agent_type} 输出失败: {save_err}")

            # 推送 completed 状态
            completed_data = {
                "agent_type": agent_type,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            if agent.score is not None:
                completed_data["score"] = float(agent.score)
            if agent.summary:
                completed_data["summary"] = agent.summary
            await _emit_event("agent_complete", completed_data)

            # 推送 result 事件
            await _emit_event("result", {
                "agent_type": agent_type,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            })

        except Exception as e:
            logger.error(f"智能体 {agent_type} 执行失败: {e}")
            orchestrator.agent_results[agent_type] = {
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e)
            }

            # 保存失败的智能体输出
            if save_func:
                try:
                    await save_func(agent)
                except Exception as save_err:
                    logger.warning(f"保存失败智能体 {agent_type} 输出失败: {save_err}")

            await _emit_event("agent_complete", {
                "agent_type": agent_type,
                "status": "failed",
                "score": None,
                "summary": str(e)[:200],
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            })

            # 对决策智能体额外发送 error 事件
            if agent_type == "decision":
                await _emit_event("error", {
                    "error_type": "AgentError",
                    "agent_type": agent_type,
                    "message": str(e)[:200],
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                })

        finally:
            # 内部信号，不缓冲
            await event_queue.put(("_agent_done", agent_type))

    # ===== 第一阶段：运行所有分析智能体 =====
    if analysis_mode == "sequential":
        # 串行模式：按顺序逐个执行分析智能体
        for agent in orchestrator.analysis_agents:
            agent_task = asyncio.create_task(run_single_agent(agent))

            # 消费当前 agent 的事件
            while True:
                if await request.is_disconnected():
                    logger.warning("客户端已断开连接，不再等待分析事件")
                    raise asyncio.CancelledError("客户端已断开连接")
                try:
                    event_type, data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if agent_task.done():
                        break
                    continue

                if event_type == "_agent_done":
                    break
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

            await agent_task

            # 将当前 agent 的结果注入 context，供后续 agent 参考
            context["agent_results"] = orchestrator.agent_results
    else:
        # 并行模式：同时运行所有分析智能体
        analysis_tasks = [
            asyncio.create_task(run_single_agent(agent))
            for agent in orchestrator.analysis_agents
        ]

        analysis_count = len(orchestrator.analysis_agents)
        completed_count = 0

        # 消费分析 agent 的事件（实时交错推送）
        while completed_count < analysis_count:
            # 客户端断开检测
            if await request.is_disconnected():
                logger.warning("客户端已断开连接，不再等待分析事件")
                # 注意：不取消 analysis_tasks 中的任务，避免中断 V8/mini-racer 操作
                # 导致进程级崩溃（py_mini_racer 不支持并发中断）
                raise asyncio.CancelledError("客户端已断开连接")
            try:
                event_type, data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            if event_type == "_agent_done":
                completed_count += 1
            else:
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

        # 等待所有分析 agent 完成（收集可能的异常）
        await asyncio.gather(*analysis_tasks, return_exceptions=True)

    # ===== 第二阶段：运行决策智能体 =====
    context["agent_results"] = orchestrator.agent_results
    decision_task = asyncio.create_task(run_single_agent(orchestrator.decision_agent))

    # 消费决策 agent 的事件
    while True:
        # 客户端断开检测
        if await request.is_disconnected():
            logger.warning("客户端已断开连接，不再等待决策分析事件")
            # 不取消 decision_task，避免中断 V8/mini-racer 操作
            raise asyncio.CancelledError("客户端已断开连接")
        try:
            event_type, data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            if decision_task.done():
                break
            continue

        if event_type == "_agent_done":
            break
        else:
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
    await decision_task

    # 清理回调
    for agent in orchestrator.analysis_agents:
        agent.set_thinking_callback(None)
        agent.set_streaming_thinking_callback(None)
        agent.set_tool_call_callback(None)
    if orchestrator.decision_agent:
        orchestrator.decision_agent.set_thinking_callback(None)
        orchestrator.decision_agent.set_streaming_thinking_callback(None)
        orchestrator.decision_agent.set_tool_call_callback(None)

    # 向重连的 SSE 连接发送分析完成信号，然后清理全局队列和缓冲区
    if session_id:
        try:
            # 发送完成信号（给异步等待的重连连接）
            await event_queue.put(("_analysis_done", {"session_id": session_id}))
        except Exception:
            pass  # 队列可能已关闭
        async with _active_queues_lock:
            _active_event_queues.pop(session_id, None)
        # 清理缓冲区和运行中智能体追踪
        _active_event_buffers.pop(session_id, None)
        _active_running_agents.pop(session_id, None)
