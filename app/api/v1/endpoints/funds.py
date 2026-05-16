"""
基金API端点
提供基金搜索、详情、净值历史、持仓、费率等查询功能
"""
import logging
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
import json

from app.core.database import get_async_session
from app.core.cache import get_cache, CacheKeys, CacheExpire, CacheClient
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
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/funds", tags=["基金"])


@router.get("/search", response_model=ApiResponse[PaginatedData[FundListItem]])
async def search_funds(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="基金类型"),
    session: AsyncSession = Depends(get_async_session),
    cache: CacheClient = Depends(get_cache),
):
    """搜索基金"""
    # 首先尝试从数据库搜索
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

    # 计算总数（使用 SELECT COUNT 避免加载全部数据到内存）
    count_query = select(func.count(Fund.id))
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
    db_total = total_result.scalar() or 0

    # 如果数据库中没有结果，尝试从数据源搜索
    if db_total == 0:
        try:
            # 从数据源搜索基金（会自动初始化）
            search_results = await datasource_manager.search_funds(keyword, limit=size)

            if search_results:
                # 构建响应
                items = [
                    FundListItem(
                        fund_code=item.get("fund_code", ""),
                        fund_name=item.get("fund_name", ""),
                        fund_type=item.get("fund_type", ""),
                        purchase_status="开放",
                        current_scale=item.get("scale")
                    )
                    for item in search_results
                ]

                return ApiResponse(
                    code=200,
                    message="success",
                    data=PaginatedData(
                        total=len(items),
                        page=page,
                        size=size,
                        total_pages=1,
                        items=items
                    )
                )
        except Exception as e:
            logger.error(f"从数据源搜索基金失败: {e}")

    # 从数据库分页获取
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

    total_pages = (db_total + size - 1) // size

    return ApiResponse(
        code=200,
        message="success",
        data=PaginatedData(
            total=db_total,
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
    cache: CacheClient = Depends(get_cache),
):
    """获取基金详情"""
    # 尝试从缓存获取
    cache_key = CacheKeys.FUND_INFO.format(fund_code=fund_code)
    cached_data = await cache.get(cache_key)

    if cached_data:
        fund_data = json.loads(cached_data)
        return ApiResponse(code=200, message="success", data=FundDetail(**fund_data))

    # 查询数据库中的基金信息
    result = await session.execute(
        select(Fund).where(Fund.fund_code == fund_code)
    )
    fund = result.scalar_one_or_none()

    # 如果数据库中没有，尝试从数据源获取
    if not fund:
        try:
            # 从数据源获取基金信息（会自动初始化）
            fund_info = await datasource_manager.get_fund_info(fund_code)

            if fund_info:
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
                    fund_code=fund_info.get("fund_code", fund_code),
                    fund_name=fund_info.get("fund_name", "未知基金"),
                    fund_type=fund_info.get("fund_type", ""),
                    fund_manager=fund_info.get("fund_manager"),
                    establish_date=fund_info.get("establish_date"),
                    current_scale=fund_info.get("scale"),
                    management_fee=fund_info.get("management_fee"),
                    custody_fee=fund_info.get("custody_fee"),
                    purchase_status="开放",
                    redemption_status="开放",
                    benchmark=None,
                    is_qdii=False,
                    share_class="A",
                    latest_nav=LatestNav(
                        nav_date=latest_nav.nav_date if latest_nav else None,
                        unit_nav=latest_nav.unit_nav if latest_nav else None,
                        accumulated_nav=latest_nav.accumulated_nav if latest_nav else None,
                        daily_growth_rate=latest_nav.daily_growth_rate if latest_nav else None
                    ) if latest_nav else None
                )

                # 缓存结果
                await cache.set(
                    cache_key,
                    json.dumps(fund_detail.model_dump(), default=str),
                    expire=CacheExpire.FUND_INFO
                )

                return ApiResponse(code=200, message="success", data=fund_detail)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="基金不存在"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据源获取基金信息失败: {e}")
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
    await cache.set(
        cache_key,
        json.dumps(fund_detail.model_dump(), default=str),
        expire=CacheExpire.FUND_INFO
    )

    return ApiResponse(code=200, message="success", data=fund_detail)


@router.get("/compare", response_model=ApiResponse)
async def compare_funds(
    fund_codes: str = Query(..., description="基金代码列表，逗号分隔，最多5只"),
    session: AsyncSession = Depends(get_async_session),
):
    """对比多只基金的关键指标"""
    codes = [c.strip() for c in fund_codes.split(",") if c.strip()]
    if not codes:
        raise HTTPException(status_code=400, detail="请提供至少一只基金代码")
    if len(codes) > 5:
        raise HTTPException(status_code=400, detail="最多对比5只基金")

    from app.core.calculations import (
        calculate_volatility, calculate_max_drawdown, calculate_sharpe_ratio,
        calculate_style_box, calculate_dca_analysis
    )
    import numpy as np

    comparison_results = []
    for code in codes:
        try:
            fund_info = await datasource_manager.get_fund_info(code)
            nav_history = await datasource_manager.get_nav_history(
                code,
                start_date=date.today() - timedelta(days=365),
                end_date=date.today()
            )
            holdings = await datasource_manager.get_holdings(code)
            fees = await datasource_manager.get_fund_fees(code)

            fund_data = {
                "fund_code": code,
                "fund_name": fund_info.get("fund_name", "未知") if fund_info else "未知",
                "fund_type": fund_info.get("fund_type", "") if fund_info else "",
                "fund_manager": fund_info.get("fund_manager", "") if fund_info else "",
                "scale": fund_info.get("scale") if fund_info else None,
            }

            if nav_history and len(nav_history) > 20:
                nav_values = np.array([
                    float(d.get("nav", 0)) for d in nav_history
                ])
                nav_values = nav_values[nav_values > 0]

                if len(nav_values) > 20:
                    returns = np.diff(nav_values) / nav_values[:-1]
                    fund_data["volatility"] = calculate_volatility(returns)
                    max_dd, _ = calculate_max_drawdown(nav_values)
                    fund_data["max_drawdown"] = max_dd
                    fund_data["sharpe_ratio"] = calculate_sharpe_ratio(returns)
                    fund_data["current_nav"] = float(nav_values[-1])
                    fund_data["nav_count"] = len(nav_values)

                    annual_return = (nav_values[-1] / nav_values[0] - 1) * 252 / len(nav_values) * 100
                    fund_data["annual_return"] = round(annual_return, 2)

            if holdings:
                style = calculate_style_box(holdings)
                if style.get("data_sufficient"):
                    fund_data["style_box"] = style["style_box_position"]
                    fund_data["market_cap_style"] = style["market_cap_style"]
                    fund_data["value_style"] = style["value_style"]

            if fees:
                fund_data["purchase_fee"] = fees.get("purchase_fee")
                fund_data["management_fee"] = fees.get("management_fee")

            comparison_results.append(fund_data)

        except Exception as e:
            logger.error(f"对比分析基金 {code} 失败: {e}")
            comparison_results.append({
                "fund_code": code,
                "fund_name": "获取失败",
                "error": str(e)
            })

    return ApiResponse(
        code=200,
        message="success",
        data={"funds": comparison_results, "count": len(comparison_results)}
    )


@router.get("/{fund_code}/nav", response_model=ApiResponse[NavHistoryResponse])
async def get_fund_nav_history(
    fund_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    session: AsyncSession = Depends(get_async_session),
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
        # 尝试从数据源获取基金名称（会自动初始化）
        try:
            fund_info = await datasource_manager.get_fund_info(fund_code)
            if fund_info:
                fund_name = fund_info.get("fund_name", "未知基金")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="基金不存在"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据源获取基金信息失败: {e}")
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

    # 如果数据库中没有净值数据，尝试从数据源获取
    if not nav_list:
        try:
            # 从数据源获取净值历史（会自动初始化）
            nav_data = await datasource_manager.get_nav_history(fund_code, start_date, end_date)

            if nav_data:
                nav_data_list = [
                    NavData(
                        nav_date=item.get("trade_date"),
                        unit_nav=item.get("unit_nav"),
                        accumulated_nav=item.get("accumulated_nav"),
                        daily_growth_rate=item.get("daily_return")
                    )
                    for item in nav_data[:limit]
                ]

                return ApiResponse(
                    code=200,
                    message="success",
                    data=NavHistoryResponse(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        nav_data=nav_data_list
                    )
                )
        except Exception as e:
            logger.error(f"从数据源获取净值历史失败: {e}")

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
):
    """获取基金持仓"""
    # 查询最新报告期的持仓
    result = await session.execute(
        select(FundHolding)
        .where(FundHolding.fund_code == fund_code)
        .order_by(FundHolding.report_date.desc())
    )
    holdings = result.scalars().all()

    # 如果数据库中没有持仓数据，尝试从数据源获取
    if not holdings:
        try:
            # 从数据源获取持仓信息（会自动初始化）
            holdings_data = await datasource_manager.get_holdings(fund_code)

            if holdings_data:
                # 构建持仓列表
                holding_items = []
                stocks = holdings_data.get("stocks", [])
                for stock in stocks:
                    holding_items.append(HoldingItem(
                        stock_code=stock.get("stock_code", ""),
                        stock_name=stock.get("stock_name", ""),
                        holding_ratio=stock.get("holding_ratio"),
                        holding_value=stock.get("holding_value"),
                        industry=stock.get("industry", "")
                    ))

                # 计算行业分布
                industry_distribution = {}
                for stock in stocks:
                    industry = stock.get("industry")
                    ratio = stock.get("holding_ratio")
                    if industry and ratio:
                        industry_distribution[industry] = industry_distribution.get(industry, 0) + float(ratio)

                return ApiResponse(
                    code=200,
                    message="success",
                    data=HoldingsResponse(
                        fund_code=fund_code,
                        report_date=holdings_data.get("report_date"),
                        holdings=holding_items,
                        industry_distribution=industry_distribution
                    )
                )
        except Exception as e:
            logger.error(f"从数据源获取持仓信息失败: {e}")
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
):
    """获取基金费率"""
    # 查询费率信息
    result = await session.execute(
        select(FundFee)
        .where(FundFee.fund_code == fund_code)
        .order_by(FundFee.fee_type, FundFee.min_holding_days)
    )
    fees = result.scalars().all()

    # 如果数据库中没有费率数据，尝试从数据源获取
    if not fees:
        try:
            # 从数据源获取费率信息（会自动初始化）
            fees_data = await datasource_manager.get_fund_fees(fund_code)

            if fees_data:
                # 构建费率列表
                fee_items = []

                # 获取赎回费率阶梯
                redemption_ladder = fees_data.get("redemption_ladder", [])
                purchase_fee = fees_data.get("purchase_fee", 0.0015)

                if redemption_ladder:
                    for item in redemption_ladder:
                        min_days = item.get("min_days", 0)
                        max_days = item.get("max_days")
                        fee_rate = item.get("fee_rate", 0)

                        if max_days:
                            period = f"{min_days}-{max_days}天"
                        else:
                            period = f"{min_days}天以上"

                        total_fee = purchase_fee + fee_rate
                        fee_items.append(FeeItem(
                            holding_period=period,
                            purchase_fee=f"{purchase_fee * 100:.2f}%",
                            redemption_fee=f"{fee_rate * 100:.2f}%",
                            total_fee=f"{total_fee * 100:.2f}%",
                            breakeven=f"约{total_fee * 100:.2f}%"
                        ))
                else:
                    # 使用默认费率
                    default_fees = [
                        FeeItem(holding_period="7天", purchase_fee="0.15%", redemption_fee="1.50%", total_fee="1.65%", breakeven="约1.68%"),
                        FeeItem(holding_period="15天", purchase_fee="0.15%", redemption_fee="0.75%", total_fee="0.90%", breakeven="约0.91%"),
                        FeeItem(holding_period="30天", purchase_fee="0.15%", redemption_fee="0.50%", total_fee="0.65%", breakeven="约0.66%"),
                        FeeItem(holding_period="180天", purchase_fee="0.15%", redemption_fee="0.25%", total_fee="0.40%", breakeven="约0.40%"),
                        FeeItem(holding_period="1年", purchase_fee="0.15%", redemption_fee="0.00%", total_fee="0.15%", breakeven="约0.15%")
                    ]
                    fee_items = default_fees

                return ApiResponse(
                    code=200,
                    message="success",
                    data=FeesResponse(fund_code=fund_code, fees=fee_items)
                )
        except Exception as e:
            logger.error(f"从数据源获取费率信息失败: {e}")
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
