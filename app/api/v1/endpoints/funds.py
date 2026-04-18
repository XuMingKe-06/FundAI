"""
基金API端点
"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from redis.asyncio import Redis
import json

from app.core.database import get_async_session
from app.core.redis_client import get_redis, CacheKeys, CacheExpire
from app.core.security import get_current_user
from app.models.user import User
from app.models.fund import Fund, FundNav, FundHolding, FundFee
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.fund import (
    FundListItem,
    FundDetail,
    LatestNav,
    NavData,
    NavHistoryResponse,
    HoldingItem,
    HoldingsResponse,
    FeeItem,
    FeesResponse
)

router = APIRouter(prefix="/funds", tags=["基金"])


@router.get("/search", response_model=ApiResponse[PaginatedData[FundListItem]])
async def search_funds(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="基金类型"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """搜索基金"""
    # 构建查询
    query = select(Fund).where(Fund.fund_code != "")
    
    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                Fund.fund_code.contains(keyword),
                Fund.fund_name.contains(keyword)
            )
        )
    
    # 类型过滤
    if type:
        query = query.where(Fund.fund_type == type)
    
    # 计算总数
    count_query = select(Fund.fund_code)
    if keyword:
        count_query = count_query.where(
            or_(
                Fund.fund_code.contains(keyword),
                Fund.fund_name.contains(keyword)
            )
        )
    if type:
        count_query = count_query.where(Fund.fund_type == type)
    
    total_result = await session.execute(count_query)
    total = len(total_result.all())
    
    # 分页
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    
    result = await session.execute(query)
    funds = result.scalars().all()
    
    # 构建响应
    items = [
        FundListItem(
            fund_code=fund.fund_code,
            fund_name=fund.fund_name,
            fund_type=fund.fund_type,
            purchase_status=fund.purchase_status,
            current_scale=fund.current_scale
        )
        for fund in funds
    ]
    
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


@router.get("/{fund_code}", response_model=ApiResponse[FundDetail])
async def get_fund_detail(
    fund_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """获取基金详情"""
    # 尝试从缓存获取
    cache_key = CacheKeys.FUND_INFO.format(fund_code=fund_code)
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        fund_data = json.loads(cached_data)
        return ApiResponse(code=200, message="success", data=FundDetail(**fund_data))
    
    # 查询基金信息
    result = await session.execute(
        select(Fund).where(Fund.fund_code == fund_code)
    )
    fund = result.scalar_one_or_none()
    
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="基金不存在"
        )
    
    # 查询最新净值
    nav_result = await session.execute(
        select(FundNav)
        .where(FundNav.fund_code == fund_code)
        .order_by(FundNav.nav_date.desc())
        .limit(1)
    )
    latest_nav = nav_result.scalar_one_or_none()
    
    # 构建响应
    fund_detail = FundDetail(
        fund_code=fund.fund_code,
        fund_name=fund.fund_name,
        fund_type=fund.fund_type,
        fund_manager=fund.fund_manager,
        establish_date=fund.establish_date,
        current_scale=fund.current_scale,
        management_fee=fund.management_fee,
        custody_fee=fund.custody_fee,
        purchase_status=fund.purchase_status,
        redemption_status=fund.redemption_status,
        benchmark=fund.benchmark,
        is_qdii=fund.is_qdii,
        share_class=fund.share_class,
        latest_nav=LatestNav(
            nav_date=latest_nav.nav_date,
            unit_nav=latest_nav.unit_nav,
            accumulated_nav=latest_nav.accumulated_nav,
            daily_growth_rate=latest_nav.daily_growth_rate
        ) if latest_nav else None
    )
    
    # 缓存结果
    await redis.setex(
        cache_key,
        CacheExpire.FUND_INFO,
        json.dumps(fund_detail.model_dump(), default=str)
    )
    
    return ApiResponse(code=200, message="success", data=fund_detail)


@router.get("/{fund_code}/nav", response_model=ApiResponse[NavHistoryResponse])
async def get_fund_nav_history(
    fund_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取基金净值历史"""
    # 默认查询最近3个月
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    if not end_date:
        end_date = date.today()
    
    # 查询基金名称
    fund_result = await session.execute(
        select(Fund.fund_name).where(Fund.fund_code == fund_code)
    )
    fund_name = fund_result.scalar_one_or_none()
    
    if not fund_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="基金不存在"
        )
    
    # 查询净值历史
    result = await session.execute(
        select(FundNav)
        .where(FundNav.fund_code == fund_code)
        .where(FundNav.nav_date >= start_date)
        .where(FundNav.nav_date <= end_date)
        .order_by(FundNav.nav_date.desc())
        .limit(limit)
    )
    nav_list = result.scalars().all()
    
    # 构建响应
    nav_data = [
        NavData(
            nav_date=nav.nav_date,
            unit_nav=nav.unit_nav,
            accumulated_nav=nav.accumulated_nav,
            daily_growth_rate=nav.daily_growth_rate
        )
        for nav in nav_list
    ]
    
    return ApiResponse(
        code=200,
        message="success",
        data=NavHistoryResponse(
            fund_code=fund_code,
            fund_name=fund_name,
            nav_data=nav_data
        )
    )


@router.get("/{fund_code}/holdings", response_model=ApiResponse[HoldingsResponse])
async def get_fund_holdings(
    fund_code: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取基金持仓"""
    # 查询最新报告期的持仓
    result = await session.execute(
        select(FundHolding)
        .where(FundHolding.fund_code == fund_code)
        .order_by(FundHolding.report_date.desc())
    )
    holdings = result.scalars().all()
    
    if not holdings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无持仓数据"
        )
    
    # 获取报告期
    report_date = holdings[0].report_date
    
    # 构建持仓列表
    holding_items = [
        HoldingItem(
            stock_code=h.stock_code,
            stock_name=h.stock_name,
            holding_ratio=h.holding_ratio,
            holding_value=h.holding_value,
            industry=h.industry
        )
        for h in holdings
    ]
    
    # 计算行业分布
    industry_distribution = {}
    for h in holdings:
        if h.industry and h.holding_ratio:
            industry_distribution[h.industry] = industry_distribution.get(h.industry, 0) + float(h.holding_ratio)
    
    return ApiResponse(
        code=200,
        message="success",
        data=HoldingsResponse(
            fund_code=fund_code,
            report_date=report_date,
            holdings=holding_items,
            industry_distribution=industry_distribution
        )
    )


@router.get("/{fund_code}/fees", response_model=ApiResponse[FeesResponse])
async def get_fund_fees(
    fund_code: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取基金费率"""
    # 查询费率信息
    result = await session.execute(
        select(FundFee)
        .where(FundFee.fund_code == fund_code)
        .order_by(FundFee.fee_type, FundFee.min_holding_days)
    )
    fees = result.scalars().all()
    
    if not fees:
        # 返回默认费率
        default_fees = [
            FeeItem(holding_period="7天", purchase_fee="0.15%", redemption_fee="1.50%", total_fee="1.65%", breakeven="约1.68%"),
            FeeItem(holding_period="15天", purchase_fee="0.15%", redemption_fee="0.75%", total_fee="0.90%", breakeven="约0.91%"),
            FeeItem(holding_period="30天", purchase_fee="0.15%", redemption_fee="0.50%", total_fee="0.65%", breakeven="约0.66%"),
            FeeItem(holding_period="180天", purchase_fee="0.15%", redemption_fee="0.25%", total_fee="0.40%", breakeven="约0.40%"),
            FeeItem(holding_period="1年", purchase_fee="0.15%", redemption_fee="0.00%", total_fee="0.15%", breakeven="约0.15%")
        ]
        return ApiResponse(
            code=200,
            message="success",
            data=FeesResponse(fund_code=fund_code, fees=default_fees)
        )
    
    # 构建费率列表
    fee_items = []
    for fee in fees:
        if fee.fee_type == "redemption":
            period = f"{fee.min_holding_days or 0}-{fee.max_holding_days or '+'}天"
            total = float(fee.fee_rate) + 0.0015  # 加上申购费
            breakeven = f"约{total * 100:.2f}%"
            fee_items.append(FeeItem(
                holding_period=period,
                purchase_fee="0.15%",
                redemption_fee=f"{float(fee.fee_rate) * 100:.2f}%",
                total_fee=f"{total * 100:.2f}%",
                breakeven=breakeven
            ))
    
    return ApiResponse(
        code=200,
        message="success",
        data=FeesResponse(fund_code=fund_code, fees=fee_items)
    )
