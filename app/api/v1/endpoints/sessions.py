"""
会话管理API端点（无需认证）
"""
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete, func
from sqlalchemy.orm import joinedload

from app.core.database import get_async_session
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, AgentOutput, DecisionReport
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.analysis import SessionListItem, SessionDetail, AgentOutputInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["会话"])


@router.get("", response_model=ApiResponse[PaginatedData[SessionListItem]])
async def get_sessions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取所有会话列表（无需认证）"""

    # 构建查询，使用 joinedload 预先加载 fund 和 report 关联，避免 N+1
    query = (
        select(AnalysisSession)
        .options(joinedload(AnalysisSession.fund), joinedload(AnalysisSession.report))
    )

    if status:
        query = query.where(AnalysisSession.status == status)

    # 计算总数（使用 SELECT COUNT 避免加载全部数据到内存）
    count_query = select(func.count(AnalysisSession.id))
    if status:
        count_query = count_query.where(AnalysisSession.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * size
    query = query.order_by(desc(AnalysisSession.created_at)).offset(offset).limit(size)

    result = await session.execute(query)
    # unique() 必须调用，因为 joinedload 会产生重复行
    sessions = result.unique().scalars().all()

    # 构建响应列表（直接从已加载的关联中读取，无需额外查询）
    items = []
    for s in sessions:
        fund_name = s.fund.fund_name if s.fund else "未知基金"

        # 从决策报告中提取长短线方向
        short_term_direction = None
        long_term_direction = None
        if s.status == "completed" and s.report:
            short_term_decision = s.report.short_term_decision or {}
            long_term_decision = s.report.long_term_decision or {}
            short_term_direction = _direction_to_chinese(short_term_decision.get("direction"))
            long_term_direction = _direction_to_chinese(long_term_decision.get("direction"))

        items.append(SessionListItem(
            session_id=str(s.id),
            fund_code=s.fund_code,
            fund_name=fund_name,
            status=s.status,
            short_term_direction=short_term_direction,
            long_term_direction=long_term_direction,
            created_at=s.created_at,
            completed_at=s.completed_at
        ))

    total_pages = (total + size - 1) // size

    return ApiResponse(
        code=200,
        message="success",
        data=PaginatedData(
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            items=items
        )
    )


def _direction_to_chinese(direction: Optional[str]) -> Optional[str]:
    """将投资方向英文标识转换为中文"""
    if not direction:
        return None
    direction_map = {
        "buy": "买入",
        "sell": "卖出",
        "hold": "持有"
    }
    return direction_map.get(direction, direction)


@router.delete("/{session_id}", response_model=ApiResponse[None])
async def delete_session(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """删除指定的分析会话（无需认证）"""
    # 查询会话是否存在
    result = await session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session = result.scalar_one_or_none()

    if not analysis_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 级联删除关联的智能体输出和决策报告
    await session.execute(
        delete(AgentOutput).where(AgentOutput.session_id == session_id)
    )
    await session.execute(
        delete(DecisionReport).where(DecisionReport.session_id == session_id)
    )
    await session.delete(analysis_session)
    await session.commit()

    logger.info(f"会话 {session_id} 已被删除")
    return ApiResponse(code=200, message="会话已删除", data=None)


@router.get("/{session_id}", response_model=ApiResponse[SessionDetail])
async def get_session_detail(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """获取会话详情（无需认证）"""
    # 查询会话是否存在
    result = await session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session = result.scalar_one_or_none()

    if not analysis_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 查询基金名称
    fund_result = await session.execute(
        select(Fund.fund_name).where(Fund.fund_code == analysis_session.fund_code)
    )
    fund_name = fund_result.scalar_one_or_none() or "未知基金"

    # 查询智能体输出
    agent_result = await session.execute(
        select(AgentOutput).where(AgentOutput.session_id == session_id)
    )
    agent_outputs = agent_result.scalars().all()

    # 构建智能体输出列表
    agent_output_list = []
    for ao in agent_outputs:
        # 解析 thinking_process JSON 字符串
        thinking_process = None
        if ao.thinking_process:
            try:
                thinking_process = json.loads(ao.thinking_process) if isinstance(ao.thinking_process, str) else ao.thinking_process
            except (json.JSONDecodeError, TypeError):
                thinking_process = None

        # 解析 tools_called JSONB（SQLAlchemy 自动将 JSONB 转为 Python 列表）
        tools_called = ao.tools_called if ao.tools_called else None

        agent_output_list.append(AgentOutputInfo(
            agent_type=ao.agent_type,
            status=ao.status,
            score=float(ao.score) if ao.score else None,
            summary=ao.summary,
            thinking_process=thinking_process,
            tools_called=tools_called,
            duration_ms=ao.duration_ms
        ))

    # 如果没有智能体输出且会话状态为完成，记录警告日志
    if not agent_output_list and analysis_session.status not in ["pending", "running"]:
        logger.warning(f"会话 {session_id} 已完成但没有智能体输出数据")

    return ApiResponse(
        code=200,
        message="success",
        data=SessionDetail(
            session_id=str(analysis_session.id),
            fund_code=analysis_session.fund_code,
            fund_name=fund_name,
            user_preference=analysis_session.user_preference,
            status=analysis_session.status,
            created_at=analysis_session.created_at,
            completed_at=analysis_session.completed_at,
            agent_outputs=agent_output_list
        )
    )
