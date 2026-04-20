"""
分析会话API端点
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_async_session
from app.core.redis_client import get_redis, CacheKeys, CacheExpire
from app.core.security import get_current_user
from app.models.user import User
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, AgentOutput, DecisionReport
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.analysis import (
    CreateSessionRequest,
    CreateSessionResponse,
    AnalysisReport,
    SessionListItem,
    SessionDetail,
    AgentOutputInfo,
    ShortTermDecision,
    LongTermDecision,
    CostMatrixItem,
    AgentScores,
    TrendChart,
    TrendDataPoint
)
from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/sessions", response_model=ApiResponse[CreateSessionResponse])
async def create_analysis_session(
    request: CreateSessionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """创建分析会话"""
    # 查询基金信息
    result = await session.execute(
        select(Fund).where(Fund.fund_code == request.fund_code)
    )
    fund = result.scalar_one_or_none()
    
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="基金不存在"
        )
    
    # 创建分析会话
    new_session = AnalysisSession(
        user_id=current_user.id,
        fund_code=request.fund_code,
        user_preference=request.user_preference,
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
            status=new_session.status,
            created_at=new_session.created_at
        )
    )


@router.get("/sessions/{session_id}/stream")
async def stream_analysis(
    session_id: str,
    analysis_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
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
    
    # 验证权限
    if str(analysis_session_obj.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
        )
    
    # 查询基金信息
    fund_result = await analysis_session.execute(
        select(Fund).where(Fund.fund_code == analysis_session_obj.fund_code)
    )
    fund = fund_result.scalar_one_or_none()
    
    # 更新会话状态
    analysis_session_obj.status = "running"
    await analysis_session.commit()
    
    # 创建编排器实例
    orchestrator = AgentOrchestrator()
    
    # 用于存储智能体输出的列表
    agent_outputs_data = {}
    
    async def event_generator():
        """SSE事件生成器"""
        try:
            # 定义智能体列表
            agents = [
                ("fundamental", "基本面分析师"),
                ("technical", "技术分析师"),
                ("risk", "风险分析师"),
                ("cost", "成本分析师"),
                ("sentiment", "情绪分析师"),
                ("decision", "决策智能体")
            ]
            
            # 定义进度回调函数
            async def progress_callback(agent_type: str, agent_status: str, score: Optional[float], summary: Optional[str]):
                """智能体进度回调函数"""
                nonlocal agent_outputs_data
                
                # 发送智能体状态事件
                yield f"event: agent_status\ndata: {json.dumps({'agent_type': agent_type, 'status': agent_status, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                
                if agent_status == "running":
                    # 获取并发送思考过程
                    thinking_process = orchestrator.get_agent_thinking_process(agent_type)
                    for step in thinking_process:
                        if isinstance(step, dict):
                            content = step.get("text", str(step))
                        else:
                            content = str(step)
                        yield f"event: thinking\ndata: {json.dumps({'agent_type': agent_type, 'content': content, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                        await asyncio.sleep(0.1)
                
                elif agent_status == "completed":
                    # 存储智能体输出
                    agent_outputs_data[agent_type] = {
                        "status": "completed",
                        "score": score,
                        "summary": summary
                    }
                    
                    # 发送完成事件
                    yield f"event: agent_complete\ndata: {json.dumps({'agent_type': agent_type, 'status': 'completed', 'score': float(score) if score else None, 'summary': summary, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                
                elif agent_status == "failed":
                    # 发送失败事件
                    yield f"event: agent_complete\ndata: {json.dumps({'agent_type': agent_type, 'status': 'failed', 'score': None, 'summary': summary, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
            
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
                "user_preference": analysis_session_obj.user_preference
            }
            
            # 运行完整分析流程
            async for event in run_analysis_with_streaming(
                orchestrator, 
                analysis_session_obj.fund_code, 
                context, 
                progress_callback
            ):
                yield event
            
            # 保存智能体输出到数据库
            await save_agent_outputs(
                analysis_session, 
                session_id, 
                orchestrator
            )
            
            # 保存决策报告到数据库
            await save_decision_report(
                analysis_session,
                session_id,
                orchestrator
            )
            
            # 更新会话状态
            analysis_session_obj.status = "completed"
            analysis_session_obj.completed_at = datetime.utcnow()
            await analysis_session.commit()
            
            # 发送分析完成事件
            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
            
        except Exception as e:
            logger.error(f"分析过程发生错误: {e}", exc_info=True)
            
            # 更新会话状态为失败
            analysis_session_obj.status = "failed"
            await analysis_session.commit()
            
            yield f"event: error\ndata: {json.dumps({'error_type': 'AnalysisError', 'message': str(e), 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def run_analysis_with_streaming(
    orchestrator: AgentOrchestrator,
    fund_code: str,
    context: dict,
    progress_callback
):
    """运行分析并流式输出事件"""
    
    # 定义智能体列表
    agents = [
        ("fundamental", "基本面分析师"),
        ("technical", "技术分析师"),
        ("risk", "风险分析师"),
        ("cost", "成本分析师"),
        ("sentiment", "情绪分析师"),
        ("decision", "决策智能体")
    ]
    
    # 第一阶段：并行运行分析智能体
    async def run_agent_with_streaming(agent):
        """运行单个智能体并流式输出"""
        agent_type = agent.agent_type
        
        # 发送开始状态
        async for event in progress_callback(agent_type, "running", None, None):
            yield event
        
        try:
            # 运行智能体
            result = await agent.run(fund_code, context)
            
            # 发送思考过程
            for step in agent.thinking_process:
                if isinstance(step, dict):
                    content = step.get("text", str(step))
                else:
                    content = str(step)
                yield f"event: thinking\ndata: {json.dumps({'agent_type': agent_type, 'content': content, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                await asyncio.sleep(0.05)
            
            # 发送完成状态
            async for event in progress_callback(agent_type, "completed", agent.score, agent.summary):
                yield event
            
            # 发送结果事件
            yield f"event: result\ndata: {json.dumps({'agent_type': agent_type, 'result': result}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"智能体 {agent_type} 执行失败: {e}")
            async for event in progress_callback(agent_type, "failed", None, str(e)):
                yield event
            # 发送错误结果事件
            yield f"event: result\ndata: {json.dumps({'agent_type': agent_type, 'result': {'error': str(e)}}, ensure_ascii=False)}\n\n"
    
    # 并行执行所有分析智能体
    tasks = []
    for agent in orchestrator.analysis_agents:
        async def stream_agent(a=agent):
            async for event in run_agent_with_streaming(a):
                yield event
        tasks.append(stream_agent())
    
    # 收集所有智能体结果
    results = []
    for task in tasks:
        async for event in task:
            if event.startswith("event:"):
                yield event
    
    # 运行决策智能体
    decision_agent = orchestrator.decision_agent
    
    # 发送决策智能体开始状态
    async for event in progress_callback("decision", "running", None, None):
        yield event
    
    try:
        # 将分析结果加入上下文
        context["agent_results"] = orchestrator.agent_results
        
        # 运行决策智能体
        result = await decision_agent.run(fund_code, context)
        
        # 发送思考过程
        for step in decision_agent.thinking_process:
            if isinstance(step, dict):
                content = step.get("text", str(step))
            else:
                content = str(step)
            yield f"event: thinking\ndata: {json.dumps({'agent_type': 'decision', 'content': content, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
            await asyncio.sleep(0.05)
        
        # 发送完成状态
        async for event in progress_callback("decision", "completed", None, decision_agent.summary):
            yield event
        
    except Exception as e:
        logger.error(f"决策智能体执行失败: {e}")
        async for event in progress_callback("decision", "failed", None, str(e)):
            yield event


async def save_agent_outputs(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator
):
    """保存智能体输出到数据库"""
    try:
        # 保存分析智能体输出
        for agent in orchestrator.analysis_agents:
            agent_output = AgentOutput(
                session_id=session_id,
                agent_type=agent.agent_type,
                status=agent.status,
                score=agent.score,
                summary=agent.summary,
                details=agent.details,
                thinking_process=json.dumps(agent.thinking_process, ensure_ascii=False) if agent.thinking_process else None,
                tools_called=agent.tools_called if agent.tools_called else None,
                error_message=agent.error_message,
                started_at=agent.started_at or datetime.utcnow(),
                completed_at=agent.completed_at,
                duration_ms=agent.duration_ms
            )
            db_session.add(agent_output)
        
        # 保存决策智能体输出
        decision_agent = orchestrator.decision_agent
        decision_output = AgentOutput(
            session_id=session_id,
            agent_type=decision_agent.agent_type,
            status=decision_agent.status,
            score=decision_agent.score,
            summary=decision_agent.summary,
            details=decision_agent.details,
            thinking_process=json.dumps(decision_agent.thinking_process, ensure_ascii=False) if decision_agent.thinking_process else None,
            tools_called=decision_agent.tools_called if decision_agent.tools_called else None,
            error_message=decision_agent.error_message,
            started_at=decision_agent.started_at or datetime.utcnow(),
            completed_at=decision_agent.completed_at,
            duration_ms=decision_agent.duration_ms
        )
        db_session.add(decision_output)
        
        await db_session.commit()
        logger.info(f"会话 {session_id} 的智能体输出已保存")
        
    except Exception as e:
        logger.error(f"保存智能体输出失败: {e}")
        await db_session.rollback()
        raise


async def save_decision_report(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator
):
    """保存决策报告到数据库"""
    try:
        decision_agent = orchestrator.decision_agent
        details = decision_agent.details or {}
        
        # 从决策智能体详情中提取数据
        short_term_decision = details.get("short_term_decision", {})
        long_term_decision = details.get("long_term_decision", {})
        agent_scores = details.get("agent_scores", {})
        trend_data = details.get("trend_data", {})
        
        # 从成本智能体获取成本矩阵
        cost_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "cost":
                cost_agent = agent
                break
        
        cost_matrix = []
        if cost_agent and cost_agent.details:
            cost_matrix_raw = cost_agent.details.get("cost_matrix", [])
            for item in cost_matrix_raw:
                cost_matrix.append({
                    "holding_period": item.get("label", ""),
                    "purchase_fee": f"{item.get('purchase_fee', 0) * 100:.2f}%",
                    "redemption_fee": f"{item.get('redemption_fee', 0) * 100:.2f}%",
                    "total_fee": f"{item.get('total_fee', 0) * 100:.2f}%",
                    "breakeven": f"约{item.get('total_fee', 0) * 100:.2f}%"
                })
        
        # 从风险智能体获取风险提示
        risk_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "risk":
                risk_agent = agent
                break
        
        risk_alerts = []
        if risk_agent and risk_agent.details:
            risk_alerts = risk_agent.details.get("risk_alerts", [
                "持仓数据可能存在滞后",
                "市场波动风险需关注",
                "投资需谨慎"
            ])
        
        # 构建趋势图数据
        trend_chart = None
        if trend_data:
            historical = trend_data.get("historical", [])
            predicted = trend_data.get("predicted", [])
            
            trend_chart = {
                "historical_data": [
                    {
                        "date": item.get("date", ""),
                        "value": item.get("nav", 0)
                    }
                    for item in historical
                ],
                "prediction_data": [
                    {
                        "date": item.get("date", ""),
                        "value": item.get("nav", 0),
                        "upper_bound": item.get("upper_bound"),
                        "lower_bound": item.get("lower_bound")
                    }
                    for item in predicted
                ],
                "chart_config": {
                    "historical_color": "#3B82F6",
                    "prediction_color": "#F97316",
                    "historical_label": "历史走势",
                    "prediction_label": "预测走势"
                }
            }
        
        # 创建决策报告
        report = DecisionReport(
            session_id=session_id,
            short_term_decision=short_term_decision,
            long_term_decision=long_term_decision,
            cost_matrix=cost_matrix,
            risk_alerts=risk_alerts,
            agent_scores=agent_scores,
            trend_chart=trend_chart,
            disclaimer="本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。"
        )
        
        db_session.add(report)
        await db_session.commit()
        logger.info(f"会话 {session_id} 的决策报告已保存")
        
    except Exception as e:
        logger.error(f"保存决策报告失败: {e}")
        await db_session.rollback()
        raise


@router.get("/sessions/{session_id}/report", response_model=ApiResponse[AnalysisReport])
async def get_analysis_report(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
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
    
    # 验证权限
    if str(analysis_session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
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
        completed_at=analysis_session.completed_at or datetime.utcnow(),
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
