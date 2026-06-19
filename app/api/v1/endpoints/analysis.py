"""
分析会话API端点
提供基金分析会话的创建、SSE流式分析、报告查询等功能
"""
import json
import asyncio
from loguru import logger
from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_session, utcnow
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, AgentOutput, DecisionReport
from app.schemas.common import ApiResponse
from app.schemas.analysis import (
    CreateSessionRequest,
    CreateSessionResponse,
    AnalysisReport,
    ShortTermDecision,
    LongTermDecision,
    CostMatrixItem,
    AgentScores,
    TrendChart,
    TrendDataPoint
)
from app.agents.orchestrator import AgentOrchestrator
from app.data_sources.manager import datasource_manager
from app.services.sse_service import (
    run_analysis_with_streaming,
    _active_event_queues,
    _active_queues_lock,
    _active_event_buffers,
    _active_running_agents,
    _active_analysis_sessions,
    _active_analysis_lock,
)
from app.services.report_service import (
    save_agent_snapshot,
    save_agent_outputs,
    save_decision_report,
    save_fallback_report,
)

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/sessions", response_model=ApiResponse[CreateSessionResponse])
async def create_analysis_session(
    request: CreateSessionRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """创建分析会话"""
    logger.info("创建分析会话 | fund_code={} | preference={} | mode={}", request.fund_code, request.user_preference, request.analysis_mode)
    # 查询基金信息
    result = await session.execute(
        select(Fund).where(Fund.fund_code == request.fund_code)
    )
    fund = result.scalar_one_or_none()

    # 如果基金不在数据库中，从数据源获取并保存
    if not fund:
        logger.info(f"基金 {request.fund_code} 不在数据库中，尝试从数据源获取")

        # 从数据源获取基金信息
        fund_info = await datasource_manager.get_fund_info(request.fund_code)

        if fund_info:
            # 处理 establish_date：缓存反序列化后可能变为字符串，需转为 date 对象
            establish_date = fund_info.get("establish_date")
            if isinstance(establish_date, str):
                try:
                    establish_date = datetime.strptime(establish_date[:10], "%Y-%m-%d").date()
                except ValueError:
                    establish_date = None

            # 创建新的基金记录
            new_fund = Fund(
                fund_code=fund_info.get("fund_code", request.fund_code),
                fund_name=fund_info.get("fund_name", "未知基金"),
                fund_type=fund_info.get("fund_type"),
                fund_manager=fund_info.get("fund_manager"),
                establish_date=establish_date,
                current_scale=fund_info.get("current_scale"),
                management_fee=fund_info.get("management_fee"),
            )
            session.add(new_fund)
            await session.commit()
            await session.refresh(new_fund)
            fund = new_fund
            logger.info("从数据源创建基金记录 | fund_code={} | fund_name={}", fund.fund_code, fund.fund_name)
        else:
            # 数据源也没有，返回错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"基金 {request.fund_code} 不存在，请检查基金代码是否正确"
            )

    # 创建分析会话（不再关联用户）
    new_session = AnalysisSession(
        fund_code=request.fund_code,
        user_preference=request.user_preference,
        analysis_mode=request.analysis_mode,
        previous_session_id=request.previous_session_id,
        status="pending"
    )

    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)

    return ApiResponse(
        code=200,
        message="分析会话创建成功",
        data=CreateSessionResponse(
            session_id=str(new_session.id),
            fund_code=new_session.fund_code,
            fund_name=fund.fund_name,
            user_preference=new_session.user_preference,
            analysis_mode=new_session.analysis_mode,
            status=new_session.status,
            created_at=new_session.created_at
        )
    )


@router.get("/sessions/{session_id}/stream")
async def stream_analysis(
    session_id: str,
    request: Request,
    analysis_session: AsyncSession = Depends(get_async_session)
):
    """启动分析并通过SSE流式输出"""
    # 查询会话
    result = await analysis_session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session_obj = result.scalar_one_or_none()

    if not analysis_session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    logger.info("启动分析流 | session_id={} | fund_code={} | mode={}", session_id, analysis_session_obj.fund_code, analysis_session_obj.analysis_mode)

    # 如果会话已完成或失败，直接返回对应事件（处理前端重连场景）
    if analysis_session_obj.status == "completed":
        async def completed_event_generator():
            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
        return StreamingResponse(
            completed_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    if analysis_session_obj.status == "failed":
        async def failed_event_generator():
            yield f"event: error\ndata: {json.dumps({'error_type': 'SessionFailed', 'message': '该分析任务已失败，请重新分析', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
        return StreamingResponse(
            failed_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # 如果会话状态为 running，检查是否有活跃的事件队列（页面刷新重连场景）
    if analysis_session_obj.status == "running":
        async with _active_queues_lock:
            existing_queue = _active_event_queues.get(session_id)
        if existing_queue is not None:
            logger.info("分析流重连 | session_id={} | 复用已有队列", session_id)

            # 先加载已有 agent outputs，在 reconnect_generator 中作为初始事件发送
            agent_outputs_result = await analysis_session.execute(
                select(AgentOutput).where(AgentOutput.session_id == session_id)
            )
            existing_outputs_list = agent_outputs_result.scalars().all()

            async def reconnect_generator():
                """重连生成器：先发送快照和运行中智能体状态，再回放缓冲区事件，最后从队列消费"""
                # ---- 第1步：发送已完成智能体的快照（从数据库） ----
                completed_agent_types: set[str] = set()
                for ao in existing_outputs_list:
                    thinking_process = None
                    if ao.thinking_process:
                        try:
                            thinking_process = json.loads(ao.thinking_process) if isinstance(ao.thinking_process, str) else ao.thinking_process
                        except (json.JSONDecodeError, TypeError):
                            thinking_process = None
                    tools_called = ao.tools_called if ao.tools_called else None
                    status_str = "error" if ao.status == "failed" else ao.status
                    score_val = float(ao.score) if ao.score else None
                    snapshot_data = {
                        "agent_type": ao.agent_type,
                        "status": status_str,
                        "score": score_val,
                        "summary": ao.summary,
                        "thinking_process": thinking_process,
                        "tools_called": tools_called,
                        "duration_ms": ao.duration_ms,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                    completed_agent_types.add(ao.agent_type)
                    yield f"event: agent_snapshot\ndata: {json.dumps(snapshot_data, ensure_ascii=False, default=str)}\n\n"

                # ---- 第2步：发送运行中智能体的 agent_status 事件 ----
                running_agents = _active_running_agents.get(session_id, set()).copy()
                for agent_type in running_agents:
                    if agent_type not in completed_agent_types:
                        yield f"event: agent_status\ndata: {json.dumps({'agent_type': agent_type, 'status': 'running', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"

                # ---- 第3步：回放缓冲区中运行中智能体的历史事件 ----
                buffer_snapshot = list(_active_event_buffers.get(session_id, []))
                for buf_event_type, buf_data in buffer_snapshot:
                    # 跳过内部信号
                    if buf_event_type in ("_agent_done", "_analysis_done"):
                        continue
                    # 跳过已完成智能体的事件（已通过 agent_snapshot 发送完整快照）
                    buf_agent_type = buf_data.get("agent_type") if isinstance(buf_data, dict) else None
                    if buf_agent_type and buf_agent_type in completed_agent_types:
                        continue
                    # 跳过 agent_status 事件（已在第2步中发送）
                    if buf_event_type == "agent_status":
                        continue
                    yield f"event: {buf_event_type}\ndata: {json.dumps(buf_data, ensure_ascii=False, default=str)}\n\n"

                # ---- 第4步：从已有队列消费后续事件 ----
                try:
                    while True:
                        try:
                            event_type, data = await asyncio.wait_for(existing_queue.get(), timeout=0.5)
                        except asyncio.TimeoutError:
                            # 超时检查 session 是否已完成
                            async with _active_analysis_lock:
                                still_active = session_id in _active_analysis_sessions
                            if not still_active:
                                # 分析已完成，判断最终状态
                                await analysis_session.refresh(analysis_session_obj)
                                if analysis_session_obj.status == "completed":
                                    yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
                                else:
                                    yield f"event: error\ndata: {json.dumps({'error_type': 'SessionFailed', 'message': '分析任务已结束', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
                                return
                            continue

                        if event_type == "_analysis_done":
                            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
                            return
                        if event_type in ("_agent_done",):
                            continue  # 内部信号，不转发
                        yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
                except asyncio.CancelledError:
                    logger.info("客户端断开连接 | session_id={} | 阶段=重连流消费", session_id)
            return StreamingResponse(
                reconnect_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
            )

    # 查询基金信息
    fund_result = await analysis_session.execute(
        select(Fund).where(Fund.fund_code == analysis_session_obj.fund_code)
    )
    fund = fund_result.scalar_one_or_none()

    # 并发跟踪：记录正在分析的会话（仅用于断开检测后的清理）
    async with _active_analysis_lock:
        _active_analysis_sessions.add(session_id)

    # 更新会话状态
    analysis_session_obj.status = "running"
    await analysis_session.commit()

    # 创建编排器实例
    orchestrator = AgentOrchestrator()

    async def event_generator():
        """SSE事件生成器"""
        try:
            # 构建分析上下文
            context = {
                "fund_info": {
                    "fund_code": analysis_session_obj.fund_code,
                    "fund_name": fund.fund_name if fund else "未知基金",
                    "fund_type": fund.fund_type if fund else None,
                    "fund_manager": fund.fund_manager if fund else None,
                    "establish_date": fund.establish_date if fund else None,
                    "current_scale": fund.current_scale if fund else None,
                },
                "user_preference": analysis_session_obj.user_preference,
                "analysis_mode": analysis_session_obj.analysis_mode
            }

            # 加载前次分析报告（用于重新分析场景）
            if analysis_session_obj.previous_session_id:
                try:
                    prev_report_result = await analysis_session.execute(
                        select(DecisionReport).where(
                            DecisionReport.session_id == analysis_session_obj.previous_session_id
                        )
                    )
                    prev_report = prev_report_result.scalar_one_or_none()
                    if prev_report:
                        context["previous_report"] = {
                            "analysis_date": prev_report.created_at.isoformat() if prev_report.created_at else None,
                            "short_term_decision": prev_report.short_term_decision or {},
                            "long_term_decision": prev_report.long_term_decision or {},
                            "agent_scores": prev_report.agent_scores or {},
                            "risk_alerts": prev_report.risk_alerts or [],
                        }
                        logger.info("加载前次分析报告 | prev_session_id={}", analysis_session_obj.previous_session_id)
                except Exception as e:
                    logger.warning("加载前次分析报告失败 | error={}", e)

            # 运行完整分析流程（传入 session_id 支持重连复用队列）
            async for event in run_analysis_with_streaming(
                orchestrator,
                analysis_session_obj.fund_code,
                context,
                request,
                analysis_mode=analysis_session_obj.analysis_mode,
                save_func=lambda agent: save_agent_snapshot(session_id, agent),
                session_id=session_id
            ):
                yield event

            # 保存智能体输出到数据库（允许失败，不影响报告生成）
            try:
                await save_agent_outputs(
                    analysis_session,
                    session_id,
                    orchestrator
                )
            except Exception as e:
                logger.error("保存智能体输出失败 | session_id={} | error={}", session_id, e)
                await analysis_session.rollback()

            # 保存决策报告到数据库
            report_saved = False
            try:
                await save_decision_report(
                    analysis_session,
                    session_id,
                    orchestrator
                )
                report_saved = True
            except Exception as e:
                logger.error("保存决策报告失败 | session_id={} | error={}", session_id, e)
                await analysis_session.rollback()

            # 如果正常报告保存失败，尝试保存降级报告
            if not report_saved:
                try:
                    await save_fallback_report(
                        analysis_session,
                        session_id,
                        orchestrator,
                        "部分数据获取失败，报告基于有限数据生成"
                    )
                except Exception as e:
                    logger.error("保存降级报告失败 | session_id={} | error={}", session_id, e)
                    await analysis_session.rollback()

            # 更新会话状态
            analysis_session_obj.status = "completed"
            analysis_session_obj.completed_at = utcnow()
            await analysis_session.commit()

            # 发送分析完成事件
            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"

        except Exception as e:
            logger.exception("分析过程发生错误 | session_id={} | error={}", session_id, e)

            # 更新会话状态为失败
            analysis_session_obj.status = "failed"
            await analysis_session.commit()

            yield f"event: error\ndata: {json.dumps({'error_type': 'AnalysisError', 'message': str(e), 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"
        finally:
            # 清理：从活跃会话集合中移除
            async with _active_analysis_lock:
                _active_analysis_sessions.discard(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions/{session_id}/report", response_model=ApiResponse[AnalysisReport])
async def get_analysis_report(
    session_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取分析报告"""
    # 查询会话
    result = await session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session = result.scalar_one_or_none()

    if not analysis_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 查询基金信息
    fund_result = await session.execute(
        select(Fund).where(Fund.fund_code == analysis_session.fund_code)
    )
    fund = fund_result.scalar_one_or_none()

    # 查询决策报告
    report_result = await session.execute(
        select(DecisionReport).where(DecisionReport.session_id == session_id)
    )
    decision_report = report_result.scalar_one_or_none()

    if not decision_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分析报告尚未生成，请等待分析完成"
        )

    # 构建报告响应
    short_term_data = decision_report.short_term_decision or {}
    long_term_data = decision_report.long_term_decision or {}
    cost_matrix_data = decision_report.cost_matrix or []
    agent_scores_data = decision_report.agent_scores or {}
    trend_chart_data = decision_report.trend_chart or {}

    # 构建成本矩阵
    cost_matrix = [
        CostMatrixItem(
            holding_period=item.get("holding_period", ""),
            purchase_fee=item.get("purchase_fee", ""),
            redemption_fee=item.get("redemption_fee", ""),
            total_fee=item.get("total_fee", ""),
            breakeven=item.get("breakeven", "")
        )
        for item in cost_matrix_data
    ]

    # 构建趋势图
    trend_chart = None
    if trend_chart_data:
        historical_data = [
            TrendDataPoint(
                date=item.get("date", ""),
                value=item.get("value")
            )
            for item in trend_chart_data.get("historical_data", [])
        ]

        prediction_data = [
            TrendDataPoint(
                date=item.get("date", ""),
                value=item.get("value"),
                upper_bound=item.get("upper_bound"),
                lower_bound=item.get("lower_bound")
            )
            for item in trend_chart_data.get("prediction_data", [])
        ]

        trend_chart = TrendChart(
            historical_data=historical_data,
            prediction_data=prediction_data,
            chart_config=trend_chart_data.get("chart_config", {})
        )

    # 构建智能体评分
    agent_scores = AgentScores(
        fundamental=float(agent_scores_data.get("fundamental", 3.0)),
        technical=float(agent_scores_data.get("technical", 3.0)),
        risk=float(agent_scores_data.get("risk", 3.0)),
        cost=float(agent_scores_data.get("cost", 3.0)),
        sentiment=float(agent_scores_data.get("sentiment", 0.0))
    )

    report = AnalysisReport(
        session_id=str(analysis_session.id),
        fund_code=analysis_session.fund_code,
        fund_name=fund.fund_name if fund else "未知基金",
        created_at=analysis_session.created_at,
        completed_at=analysis_session.completed_at or utcnow(),
        short_term_decision=ShortTermDecision(
            direction=short_term_data.get("direction", "hold"),
            holding_period=short_term_data.get("holding_period", ""),
            confidence=short_term_data.get("confidence", 0.5),
            reasons=short_term_data.get("reasons", []),
            stop_profit=short_term_data.get("stop_profit", ""),
            stop_loss=short_term_data.get("stop_loss", "")
        ),
        long_term_decision=LongTermDecision(
            direction=long_term_data.get("direction", "hold"),
            confidence=long_term_data.get("confidence", 0.5),
            reasons=long_term_data.get("reasons", []),
            dip_investment_suggestion=long_term_data.get("dip_investment_suggestion")
        ),
        cost_matrix=cost_matrix,
        risk_alerts=decision_report.risk_alerts or [],
        agent_scores=agent_scores,
        trend_chart=trend_chart,
        disclaimer=decision_report.disclaimer
    )

    return ApiResponse(code=200, message="success", data=report)
