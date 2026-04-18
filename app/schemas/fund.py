"""
基金相关Schema
"""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class FundSearchRequest(BaseModel):
    """基金搜索请求"""
    keyword: str = Field(..., description="搜索关键词", min_length=1)
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页数量")
    type: Optional[str] = Field(default=None, description="基金类型过滤")


class FundListItem(BaseModel):
    """基金列表项"""
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    fund_type: str = Field(..., description="基金类型")
    purchase_status: str = Field(..., description="申购状态")
    current_scale: Optional[Decimal] = Field(default=None, description="当前规模")
    
    class Config:
        from_attributes = True


class LatestNav(BaseModel):
    """最新净值"""
    nav_date: date = Field(..., description="净值日期")
    unit_nav: Decimal = Field(..., description="单位净值")
    accumulated_nav: Decimal = Field(..., description="累计净值")
    daily_growth_rate: Optional[Decimal] = Field(default=None, description="日增长率")


class FundDetail(BaseModel):
    """基金详情"""
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    fund_type: str = Field(..., description="基金类型")
    fund_manager: Optional[str] = Field(default=None, description="基金经理")
    establish_date: date = Field(..., description="成立日期")
    current_scale: Optional[Decimal] = Field(default=None, description="当前规模")
    management_fee: Optional[Decimal] = Field(default=None, description="管理费率")
    custody_fee: Optional[Decimal] = Field(default=None, description="托管费率")
    purchase_status: str = Field(..., description="申购状态")
    redemption_status: str = Field(..., description="赎回状态")
    benchmark: Optional[str] = Field(default=None, description="业绩基准")
    is_qdii: bool = Field(default=False, description="是否QDII基金")
    share_class: Optional[str] = Field(default=None, description="份额类别")
    latest_nav: Optional[LatestNav] = Field(default=None, description="最新净值")
    
    class Config:
        from_attributes = True


class NavData(BaseModel):
    """净值数据"""
    nav_date: date = Field(..., description="净值日期")
    unit_nav: Decimal = Field(..., description="单位净值")
    accumulated_nav: Decimal = Field(..., description="累计净值")
    daily_growth_rate: Optional[Decimal] = Field(default=None, description="日增长率")


class NavHistoryResponse(BaseModel):
    """净值历史响应"""
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    nav_data: List[NavData] = Field(..., description="净值数据列表")


class HoldingItem(BaseModel):
    """持仓项"""
    stock_code: Optional[str] = Field(default=None, description="股票代码")
    stock_name: Optional[str] = Field(default=None, description="股票名称")
    holding_ratio: Optional[Decimal] = Field(default=None, description="持仓占比")
    holding_value: Optional[Decimal] = Field(default=None, description="持仓市值")
    industry: Optional[str] = Field(default=None, description="所属行业")


class HoldingsResponse(BaseModel):
    """持仓响应"""
    fund_code: str = Field(..., description="基金代码")
    report_date: date = Field(..., description="报告期")
    holdings: List[HoldingItem] = Field(..., description="持仓列表")
    industry_distribution: dict = Field(..., description="行业分布")


class FeeItem(BaseModel):
    """费率项"""
    holding_period: str = Field(..., description="持有期")
    purchase_fee: str = Field(..., description="申购费率")
    redemption_fee: str = Field(..., description="赎回费率")
    total_fee: str = Field(..., description="总费率")
    breakeven: str = Field(..., description="盈亏平衡点")


class FeesResponse(BaseModel):
    """费率响应"""
    fund_code: str = Field(..., description="基金代码")
    fees: List[FeeItem] = Field(..., description="费率列表")
