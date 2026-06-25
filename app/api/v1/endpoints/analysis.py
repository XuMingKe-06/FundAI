"""
分析会话API端点
提供基金分析会话的创建、SSE流式分析、报告查询等功能
"""
import json
import asyncio
from loguru import logger
from datetime import datetime, date, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_session, utcnow
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, DecisionReport
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
from app.data_sources.manager import datasource_manager
from app.services.analysis_task_manager import analysis_task_manager
from app.services.sse_service import run_analysis_with_streaming
from app.services.report_service import save_agent_snapshot

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

    logger.info("启动分析流 | session_id={} | fund_code={} | mode={} | status={}", session_id, analysis_session_obj.fund_code, analysis_session_obj.analysis_mode, analysis_session_obj.status)

    # 如果会话已完成，直接返回完成事件（处理前端重连场景）
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

    # 如果会话已失败，直接返回错误事件
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

    # 查询基金信息
    fund_result = await analysis_session.execute(
        select(Fund).where(Fund.fund_code == analysis_session_obj.fund_code)
    )
    fund = fund_result.scalar_one_or_none()

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

    async def event_generator():
        """SSE事件生成器：委托后台任务管理器执行分析并订阅事件流"""
        try:
            # run_analysis_with_streaming 会启动或复用后台任务，并订阅其共享事件流
            async for event in run_analysis_with_streaming(
                analysis_session_obj.fund_code,
                context,
                request,
                analysis_mode=analysis_session_obj.analysis_mode,
                save_func=lambda agent: save_agent_snapshot(session_id, agent),
                session_id=session_id,
            ):
                yield event

        except Exception as e:
            logger.exception("分析流异常 | session_id={} | error={}", session_id, e)
            yield f"event: error\ndata: {json.dumps({'error_type': 'AnalysisError', 'message': str(e), 'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions/{session_id}/status", response_model=ApiResponse[Dict[str, Any]])
async def get_analysis_status(
    session_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取分析任务的实时状态（支持前端轮询或恢复时校验）"""
    result = await session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session_obj = result.scalar_one_or_none()

    if not analysis_session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 优先从内存中的任务管理器获取实时进度
    task = analysis_task_manager.get_task_sync(session_id)
    if task:
        return ApiResponse(
            code=200,
            message="success",
            data={
                "session_id": session_id,
                "fund_code": analysis_session_obj.fund_code,
                "status": task.status,
                "progress": task.progress,
                "completed_agents": list(task.completed_agents),
                "running_agents": list(task.running_agents),
                "error_message": task.error_message,
            }
        )

    # 内存中没有任务，从数据库返回
    return ApiResponse(
        code=200,
        message="success",
        data={
            "session_id": session_id,
            "fund_code": analysis_session_obj.fund_code,
            "status": analysis_session_obj.status,
            "progress": 100 if analysis_session_obj.status == "completed" else 0,
            "completed_agents": [],
            "running_agents": [],
            "error_message": None,
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
