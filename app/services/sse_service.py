"""
SSE 流式推送服务

基于 AnalysisTaskManager 提供分析事件的流式输出。
分析任务本身在后台运行，与 HTTP 连接解耦；SSE 连接仅负责订阅已有事件流。
"""
import asyncio
import json
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from fastapi import Request

from app.services.analysis_task_manager import analysis_task_manager


async def run_analysis_with_streaming(
    fund_code: str,
    context: Dict[str, Any],
    request: Request,
    analysis_mode: str = "parallel",
    save_func: Optional[Callable[[Any], Any]] = None,
    session_id: str = "",
) -> AsyncGenerator[str, None]:
    """
    运行分析并实时流式输出事件

    委托 AnalysisTaskManager 在后台启动/复用分析任务，并订阅其共享事件流。
    客户端断开时仅停止当前 SSE 流，不会中断后台分析。
    """
    # 启动或复用后台任务
    await analysis_task_manager.start(
        session_id=session_id,
        fund_code=fund_code,
        context=context,
        analysis_mode=analysis_mode,
        save_func=save_func,
    )

    # 订阅事件流（包含历史回放与实时推送；任务结束后自动退出）
    async for event in analysis_task_manager.subscribe(session_id, request=request):
        yield event
