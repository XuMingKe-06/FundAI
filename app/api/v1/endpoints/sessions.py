"""
会话管理API端点
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_async_session
from app.core.security import get_current_user
from app.models.user import User
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
    current_user: User = Depends(get_current_user)
):
    """获取用户会话列表"""
    # 构建查询
    query = select(AnalysisSession).where(AnalysisSession.user_id == current_user.id)
    
    if status:
        query = query.where(AnalysisSession.status == status)
    
    # 计算总数
    count_query = select(AnalysisSession.id).where(AnalysisSession.user_id == current_user.id)
    if status:
        count_query = count_query.where(AnalysisSession.status == status)
    
    total_result = await session.execute(count_query)
    total = len(total_result.all())
    
    # 分页
    offset = (page - 1) * size
    query = query.order_by(desc(AnalysisSession.created_at)).offset(offset).limit(size)
    
    result = await session.execute(query)
    sessions = result.scalars().all()
    
    # 构建响应
    items = []
    for s in sessions:
        # 查询基金名称
        fund_result = await session.execute(
            select(Fund.fund_name).where(Fund.fund_code == s.fund_code)
        )
        fund_name = fund_result.scalar_one_or_none() or "未知基金"
        
        # 查询决策方向
        short_term_direction = None
        long_term_direction = None
        if s.status == "completed":
            # 从决策报告中获取方向
            report_result = await session.execute(
                select(DecisionReport).where(DecisionReport.session_id == s.id)
            )
            report = report_result.scalar_one_or_none()
            if report:
                short_term_decision = report.short_term_decision or {}
                long_term_decision = report.long_term_decision or {}
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
    """将方向转换为中文"""
    if not direction:
        return None
    direction_map = {
        "buy": "买入",
        "sell": "卖出",
        "hold": "持有"
    }
    return direction_map.get(direction, direction)


@router.get("/{session_id}", response_model=ApiResponse[SessionDetail])
async def get_session_detail(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取会话详情"""
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
    agent_output_list = [
        AgentOutputInfo(
            agent_type=ao.agent_type,
            status=ao.status,
            score=float(ao.score) if ao.score else None,
            summary=ao.summary,
            duration_ms=ao.duration_ms
        )
        for ao in agent_outputs
    ]
    
    # 如果没有智能体输出且会话状态为完成，返回空列表而不是模拟数据
    # 前端应根据会话状态判断是否需要显示智能体输出
    if not agent_output_list and analysis_session.status not in ["pending", "running"]:
        logger.warning(f"会话 {session_id} 已完成但没有智能体输出数据")
    
    return ApiResponse(
        code=200,
        message="success",
        data=SessionDetail(
            session_id=str(analysis_session.id),
            user_id=str(analysis_session.user_id),
            fund_code=analysis_session.fund_code,
            fund_name=fund_name,
            user_preference=analysis_session.user_preference,
            status=analysis_session.status,
            created_at=analysis_session.created_at,
            completed_at=analysis_session.completed_at,
            agent_outputs=agent_output_list
        )
    )
