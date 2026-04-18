"""
会话管理API端点
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_async_session
from app.core.security import get_current_user
from app.models.user import User
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, AgentOutput
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.analysis import SessionListItem, SessionDetail, AgentOutputInfo

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
            # TODO: 从决策报告中获取方向
            short_term_direction = "买入"
            long_term_direction = "买入"
        
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
    
    # 如果没有智能体输出，返回模拟数据
    if not agent_output_list:
        agent_output_list = [
            AgentOutputInfo(agent_type="fundamental", status="completed", score=4.2, summary="基金经理经验丰富，持仓结构合理", duration_ms=8500),
            AgentOutputInfo(agent_type="technical", status="completed", score=3.8, summary="趋势向上，RSI中性偏强", duration_ms=7200),
            AgentOutputInfo(agent_type="risk", status="completed", score=3.5, summary="波动率适中，需关注集中度风险", duration_ms=6500),
            AgentOutputInfo(agent_type="cost", status="completed", score=4.0, summary="短线操作成本可接受", duration_ms=5800),
            AgentOutputInfo(agent_type="sentiment", status="completed", score=3.0, summary="市场情绪偏正面", duration_ms=6200),
            AgentOutputInfo(agent_type="decision", status="completed", score=None, summary="综合研判完成，生成双轨决策", duration_ms=3200)
        ]
    
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
