"""
分析会话API端点
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_async_session
from app.core.redis_client import get_redis, CacheKeys, CacheExpire
from app.core.security import get_current_user, get_current_user_from_query_or_header
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
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/sessions", response_model=ApiResponse[CreateSessionResponse])
async def create_analysis_session(
    request: CreateSessionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """创建分析会话（需要登录）"""
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
            # 创建新的基金记录
            new_fund = Fund(
                fund_code=fund_info.get("fund_code", request.fund_code),
                fund_name=fund_info.get("fund_name", "未知基金"),
                fund_type=fund_info.get("fund_type"),
                fund_manager=fund_info.get("fund_manager"),
                establish_date=fund_info.get("establish_date"),
                current_scale=fund_info.get("current_scale"),
                management_fee=fund_info.get("management_fee"),
            )
            session.add(new_fund)
            await session.commit()
            await session.refresh(new_fund)
            fund = new_fund
            logger.info(f"已从数据源创建基金记录: {fund.fund_code} - {fund.fund_name}")
        else:
            # 数据源也没有，返回错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"基金 {request.fund_code} 不存在，请检查基金代码是否正确"
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
    request: Request,
    analysis_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user_from_query_or_header)
):
    """启动分析并通过SSE流式输出（需要登录）"""
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
    
    # 验证权限（只允许会话所有者访问）
    if str(analysis_session_obj.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
        )
    
    # 如果会话已完成或失败，直接返回对应事件（处理前端重连场景）
    if analysis_session_obj.status == "completed":
        async def completed_event_generator():
            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
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
            yield f"event: error\ndata: {json.dumps({'error_type': 'SessionFailed', 'message': '该分析任务已失败，请重新分析', 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
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
                
                # 发送智能体状态事件，包含score和summary
                status_data = {'agent_type': agent_type, 'status': agent_status, 'timestamp': datetime.utcnow().isoformat() + 'Z'}
                if score is not None:
                    status_data['score'] = float(score)
                if summary is not None:
                    status_data['summary'] = summary
                yield f"event: agent_status\ndata: {json.dumps(status_data, ensure_ascii=False)}\n\n"
                
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
                    yield f"event: agent_complete\ndata: {json.dumps({'agent_type': agent_type, 'status': 'completed', 'score': float(score) if score else None, 'summary': summary, 'timestamp': datetime.utcnow().isoformat() + 'Z'}, ensure_ascii=False)}\n\n"
                
                elif agent_status == "failed":
                    # 发送失败事件，同时发送error事件以便前端展示错误信息
                    yield f"event: agent_complete\ndata: {json.dumps({'agent_type': agent_type, 'status': 'failed', 'score': None, 'summary': summary, 'timestamp': datetime.utcnow().isoformat() + 'Z'}, ensure_ascii=False)}\n\n"
                    # 对决策智能体的失败，额外发送error事件
                    if agent_type == "decision":
                        yield f"event: error\ndata: {json.dumps({'error_type': 'AgentError', 'agent_type': agent_type, 'message': summary or '决策智能体执行失败', 'timestamp': datetime.utcnow().isoformat() + 'Z'}, ensure_ascii=False)}\n\n"
            
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
            
            # 保存智能体输出到数据库（允许失败，不影响报告生成）
            try:
                await save_agent_outputs(
                    analysis_session, 
                    session_id, 
                    orchestrator
                )
            except Exception as e:
                logger.error(f"保存智能体输出失败，继续生成报告: {e}")
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
                logger.error(f"保存决策报告失败: {e}")
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
                    logger.error(f"保存降级报告也失败: {e}")
                    await analysis_session.rollback()
            
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
            
            # 将结果存入 orchestrator.agent_results，供决策智能体使用
            orchestrator.agent_results[agent_type] = result
            
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
            yield f"event: result\ndata: {json.dumps({'agent_type': agent_type, 'result': result}, ensure_ascii=False, default=str)}\n\n"
            
        except Exception as e:
            logger.error(f"智能体 {agent_type} 执行失败: {e}")
            # 即使失败也记录到 agent_results
            orchestrator.agent_results[agent_type] = {
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e)
            }
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
        # 将决策智能体标记为失败状态
        decision_agent.status = "failed"
        decision_agent.error_message = str(e)
        decision_agent.summary = f"决策智能体执行失败: {str(e)[:200]}"
        async for event in progress_callback("decision", "failed", None, decision_agent.summary):
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
            # 序列化 tools_called，确保 date 对象被转换
            tools_called_data = None
            if agent.tools_called:
                tools_called_data = json.loads(json.dumps(agent.tools_called, ensure_ascii=False, default=str))

            agent_output = AgentOutput(
                session_id=session_id,
                agent_type=agent.agent_type,
                status=agent.status,
                score=agent.score,
                summary=agent.summary,
                details=agent.details,
                thinking_process=json.dumps(agent.thinking_process, ensure_ascii=False, default=str) if agent.thinking_process else None,
                tools_called=tools_called_data,
                error_message=agent.error_message,
                started_at=agent.started_at or datetime.utcnow(),
                completed_at=agent.completed_at,
                duration_ms=agent.duration_ms
            )
            db_session.add(agent_output)
        
        # 保存决策智能体输出
        decision_agent = orchestrator.decision_agent
        # 序列化 tools_called，确保 date 对象被转换
        decision_tools_called_data = None
        if decision_agent.tools_called:
            decision_tools_called_data = json.loads(json.dumps(decision_agent.tools_called, ensure_ascii=False, default=str))

        decision_output = AgentOutput(
            session_id=session_id,
            agent_type=decision_agent.agent_type,
            status=decision_agent.status,
            score=decision_agent.score,
            summary=decision_agent.summary,
            details=decision_agent.details,
            thinking_process=json.dumps(decision_agent.thinking_process, ensure_ascii=False, default=str) if decision_agent.thinking_process else None,
            tools_called=decision_tools_called_data,
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


def _build_fallback_short_term(orchestrator: AgentOrchestrator) -> dict:
    """从各分析智能体构建降级短线决策数据"""
    reasons = []
    direction = "hold"
    
    for agent in orchestrator.analysis_agents:
        if agent.summary:
            reasons.append(f"{agent.name}：{agent.summary}")
    
    # 根据评分趋势判断方向
    tech_agent = next((a for a in orchestrator.analysis_agents if a.agent_type == "technical"), None)
    if tech_agent and tech_agent.score is not None:
        if tech_agent.score >= 4.0:
            direction = "buy"
        elif tech_agent.score <= 2.0:
            direction = "sell"
    
    if not reasons:
        reasons.append("决策智能体执行失败，基于各分析智能体摘要生成")
    
    return {
        "direction": direction,
        "holding_period": "7-15天",
        "confidence": 0.3,
        "reasons": reasons[:5],
        "stop_profit": "建议根据个人风险偏好设置",
        "stop_loss": "建议设置5%-8%止损线"
    }


def _build_fallback_long_term(orchestrator: AgentOrchestrator) -> dict:
    """从各分析智能体构建降级长线决策数据"""
    reasons = []
    direction = "hold"
    
    for agent in orchestrator.analysis_agents:
        if agent.summary:
            reasons.append(f"{agent.name}：{agent.summary}")
    
    # 根据基本面评分判断方向
    fund_agent = next((a for a in orchestrator.analysis_agents if a.agent_type == "fundamental"), None)
    if fund_agent and fund_agent.score is not None:
        if fund_agent.score >= 4.0:
            direction = "buy"
        elif fund_agent.score <= 2.0:
            direction = "sell"
    
    if not reasons:
        reasons.append("决策智能体执行失败，基于各分析智能体摘要生成")
    
    return {
        "direction": direction,
        "confidence": 0.3,
        "reasons": reasons[:5],
        "dip_investment_suggestion": "建议等待决策分析完成后再做定投决策"
    }


async def save_decision_report(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator
):
    """保存决策报告到数据库"""
    try:
        decision_agent = orchestrator.decision_agent
        details = decision_agent.details or {}
        
        # 从决策智能体详情中提取决策数据
        short_term_decision = details.get("short_term_decision", {})
        long_term_decision = details.get("long_term_decision", {})
        
        # 如果决策智能体失败，从各分析智能体构建降级决策数据
        if decision_agent.status == "failed" or not short_term_decision:
            short_term_decision = _build_fallback_short_term(orchestrator)
        if decision_agent.status == "failed" or not long_term_decision:
            long_term_decision = _build_fallback_long_term(orchestrator)
        
        # 从各分析智能体直接提取评分（而非依赖决策智能体 details 中的 agent_scores）
        agent_scores = {}
        for agent in orchestrator.analysis_agents:
            if agent.score is not None:
                agent_scores[agent.agent_type] = float(agent.score)
        # 补全缺失的评分字段
        default_scores = {"fundamental": 0.0, "technical": 0.0, "risk": 0.0, "cost": 0.0, "sentiment": 0.0}
        default_scores.update(agent_scores)
        agent_scores = default_scores
        
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
                # 成本智能体 _build_cost_matrix 使用 holding_period 和 holding_days 字段
                holding_period = item.get("holding_period", "") or item.get("label", "")
                purchase_fee = item.get("purchase_fee", 0)
                redemption_fee = item.get("redemption_fee", 0)
                total_fee = item.get("total_fee", 0)
                cost_matrix.append({
                    "holding_period": holding_period,
                    "purchase_fee": f"{purchase_fee * 100:.2f}%" if isinstance(purchase_fee, (int, float)) else str(purchase_fee),
                    "redemption_fee": f"{redemption_fee * 100:.2f}%" if isinstance(redemption_fee, (int, float)) else str(redemption_fee),
                    "total_fee": f"{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(total_fee),
                    "breakeven": f"约{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(item.get("breakeven", ""))
                })
        
        # 从风险智能体获取风险提示
        risk_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "risk":
                risk_agent = agent
                break
        
        risk_alerts = []
        if risk_agent and risk_agent.details:
            risk_alerts = risk_agent.details.get("risk_alerts", [])
        # 如果风险智能体 details 中没有 risk_alerts，生成默认提示
        if not risk_alerts:
            risk_alerts = [
                "持仓数据可能存在滞后",
                "市场波动风险需关注",
                "投资需谨慎"
            ]
        
        # 从技术智能体和编排器上下文构建趋势图数据
        trend_chart = None
        technical_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "technical":
                technical_agent = agent
                break
        
        # 尝试从技术智能体的工具调用结果中获取净值历史
        historical_data = []
        if technical_agent and technical_agent.tools_called:
            for tool_call in technical_agent.tools_called:
                if tool_call.get("name") == "get_nav_history" and tool_call.get("result", {}).get("success"):
                    nav_data = tool_call["result"].get("data", {})
                    nav_list = nav_data.get("nav_history", []) if isinstance(nav_data, dict) else []
                    if not nav_list and isinstance(nav_data, list):
                        nav_list = nav_data
                    for item in nav_list:
                        date_val = item.get("date", "") or item.get("trade_date", "")
                        nav_val = item.get("nav", 0) or item.get("unit_nav", 0)
                        if date_val and nav_val:
                            historical_data.append({
                                "date": str(date_val),
                                "value": float(nav_val)
                            })
                    break
        
        # 如果技术智能体没有净值数据，尝试从编排器上下文获取
        if not historical_data and hasattr(orchestrator, '_last_context'):
            nav_history = orchestrator._last_context.get("nav_history", [])
            for item in nav_history:
                date_val = item.get("date", "") or item.get("trade_date", "")
                nav_val = item.get("nav", 0) or item.get("unit_nav", 0)
                if date_val and nav_val:
                    historical_data.append({
                        "date": str(date_val),
                        "value": float(nav_val)
                    })
        
        if historical_data:
            # 基于历史数据生成简单预测（最近5个数据点的趋势延伸）
            prediction_data = []
            if len(historical_data) >= 5:
                last_5 = historical_data[-5:]
                avg_change = 0
                for i in range(1, len(last_5)):
                    avg_change += last_5[i]["value"] - last_5[i-1]["value"]
                avg_change /= (len(last_5) - 1)
                
                last_val = historical_data[-1]["value"]
                last_date_str = historical_data[-1]["date"]
                try:
                    base_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
                except (ValueError, IndexError):
                    base_date = datetime.utcnow()
                
                for i in range(1, 6):
                    pred_date = (base_date + timedelta(days=i * 7)).strftime("%Y-%m-%d")
                    pred_val = last_val + avg_change * i
                    prediction_data.append({
                        "date": pred_date,
                        "value": round(pred_val, 4),
                        "upper_bound": round(pred_val * 1.02, 4),
                        "lower_bound": round(pred_val * 0.98, 4)
                    })
            
            trend_chart = {
                "historical_data": historical_data,
                "prediction_data": prediction_data,
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


async def save_fallback_report(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator,
    error_msg: str = ""
):
    """保存降级报告（当正常报告生成失败时）"""
    decision_agent = orchestrator.decision_agent
    details = decision_agent.details if decision_agent else {}

    # 从各智能体获取可用评分数据
    agent_scores = {}
    for agent in orchestrator.analysis_agents:
        if agent.score is not None:
            agent_scores[agent.agent_type] = float(agent.score)

    # 补全缺失的评分字段
    default_scores = {"fundamental": 0.0, "technical": 0.0, "risk": 0.0, "cost": 0.0, "sentiment": 0.0}
    default_scores.update(agent_scores)

    # 从决策智能体获取可用的决策数据
    short_term = details.get("short_term_decision", {})
    long_term = details.get("long_term_decision", {})

    # 构建降级短线决策：优先使用决策智能体数据，否则从各分析智能体构建
    if short_term and short_term.get("direction"):
        fallback_short_term = {
            "direction": short_term.get("direction", "hold"),
            "holding_period": short_term.get("holding_period", "7-15天"),
            "confidence": short_term.get("confidence", 0.3),
            "reasons": short_term.get("reasons", ["数据获取不完整，基于有限数据生成"]),
            "stop_profit": short_term.get("stop_profit", "建议根据个人风险偏好设置"),
            "stop_loss": short_term.get("stop_loss", "建议设置5%-8%止损线")
        }
    else:
        fallback_short_term = _build_fallback_short_term(orchestrator)

    # 构建降级长线决策：优先使用决策智能体数据，否则从各分析智能体构建
    if long_term and long_term.get("direction"):
        fallback_long_term = {
            "direction": long_term.get("direction", "hold"),
            "confidence": long_term.get("confidence", 0.3),
            "reasons": long_term.get("reasons", ["数据获取不完整，基于有限数据生成"]),
            "dip_investment_suggestion": long_term.get("dip_investment_suggestion", "建议等待数据完整后再做决策")
        }
    else:
        fallback_long_term = _build_fallback_long_term(orchestrator)

    # 从成本智能体获取成本矩阵
    cost_matrix = []
    for agent in orchestrator.analysis_agents:
        if agent.agent_type == "cost" and agent.details:
            cost_matrix_raw = agent.details.get("cost_matrix", [])
            for item in cost_matrix_raw:
                holding_period = item.get("holding_period", "") or item.get("label", "")
                purchase_fee = item.get("purchase_fee", 0)
                redemption_fee = item.get("redemption_fee", 0)
                total_fee = item.get("total_fee", 0)
                cost_matrix.append({
                    "holding_period": holding_period,
                    "purchase_fee": f"{purchase_fee * 100:.2f}%" if isinstance(purchase_fee, (int, float)) else str(purchase_fee),
                    "redemption_fee": f"{redemption_fee * 100:.2f}%" if isinstance(redemption_fee, (int, float)) else str(redemption_fee),
                    "total_fee": f"{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(total_fee),
                    "breakeven": f"约{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(item.get("breakeven", ""))
                })
            break

    # 从风险智能体获取风险提示
    risk_alerts = ["分析过程中部分数据获取失败，结果仅供参考", "投资需谨慎"]
    for agent in orchestrator.analysis_agents:
        if agent.agent_type == "risk" and agent.details:
            risk_alerts = agent.details.get("risk_alerts", risk_alerts)
            break

    disclaimer_text = "本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。"
    if error_msg:
        disclaimer_text = f"本报告由AI智能体自动生成。分析过程中出现错误：{error_msg}。基于有限数据生成，不构成任何投资建议。市场有风险，投资需谨慎。"

    report = DecisionReport(
        session_id=session_id,
        short_term_decision=fallback_short_term,
        long_term_decision=fallback_long_term,
        cost_matrix=cost_matrix,
        risk_alerts=risk_alerts,
        agent_scores=default_scores,
        trend_chart=None,
        disclaimer=disclaimer_text
    )

    db_session.add(report)
    await db_session.commit()
    logger.info(f"会话 {session_id} 的降级决策报告已保存")


@router.get("/sessions/{session_id}/report", response_model=ApiResponse[AnalysisReport])
async def get_analysis_report(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取分析报告（需要登录）"""
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
    
    # 验证权限（只允许会话所有者访问）
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
