"""
基金模型 - 适配 SQLite
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, Numeric, Text, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Fund(Base):
    """基金基础信息表"""
    __tablename__ = "funds"

    # 主键，使用 String(36) 存储 UUID 字符串，兼容 SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 基金代码（6位）
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    # 基金名称
    fund_name = Column(String(200), nullable=False)
    # 基金类型（如：股票型、混合型、债券型等）
    fund_type = Column(String(50), nullable=False)
    # 基金经理
    fund_manager = Column(String(100), nullable=True)
    # 成立日期（数据源可能缺失，允许为空）
    establish_date = Column(Date, nullable=True)
    # 管理费率
    management_fee = Column(Numeric(5, 4), nullable=True)
    # 托管费率
    custody_fee = Column(Numeric(5, 4), nullable=True)
    # 当前规模（亿元）
    current_scale = Column(Numeric(20, 2), nullable=True)
    # 申购状态
    purchase_status = Column(String(20), nullable=False, default="normal")
    # 赎回状态
    redemption_status = Column(String(20), nullable=False, default="normal")
    # 业绩比较基准
    benchmark = Column(String(200), nullable=True)
    # 是否为 QDII 基金
    is_qdii = Column(Boolean, nullable=False, default=False)
    # 份额类别（A/B/C）
    share_class = Column(String(1), nullable=True)
    # 创建时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # 更新时间
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    nav_history = relationship("FundNav", back_populates="fund", cascade="all, delete-orphan")
    holdings = relationship("FundHolding", back_populates="fund", cascade="all, delete-orphan")
    fees = relationship("FundFee", back_populates="fund", cascade="all, delete-orphan")
    sessions = relationship("AnalysisSession", back_populates="fund")

    def __repr__(self):
        return f"<Fund {self.fund_code}: {self.fund_name}>"


class FundNav(Base):
    """基金净值表"""
    __tablename__ = "fund_nav"

    # 主键，使用 String(36) 存储 UUID 字符串，兼容 SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 基金代码，外键关联 funds.fund_code
    fund_code = Column(String(6), ForeignKey("funds.fund_code", ondelete="CASCADE"), nullable=False, index=True)
    # 净值日期
    nav_date = Column(Date, nullable=False)
    # 单位净值
    unit_nav = Column(Numeric(10, 4), nullable=False)
    # 累计净值
    accumulated_nav = Column(Numeric(10, 4), nullable=False)
    # 日增长率
    daily_growth_rate = Column(Numeric(8, 4), nullable=True)
    # 创建时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 联合唯一约束：同一基金同一日期仅一条净值记录
    __table_args__ = (
        UniqueConstraint("fund_code", "nav_date", name="uq_fund_nav_code_date"),
    )

    # 关联关系
    fund = relationship("Fund", back_populates="nav_history")

    def __repr__(self):
        return f"<FundNav {self.fund_code} {self.nav_date}: {self.unit_nav}>"


class FundHolding(Base):
    """基金持仓表"""
    __tablename__ = "fund_holdings"

    # 主键，使用 String(36) 存储 UUID 字符串，兼容 SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 基金代码，外键关联 funds.fund_code
    fund_code = Column(String(6), ForeignKey("funds.fund_code", ondelete="CASCADE"), nullable=False, index=True)
    # 报告期
    report_date = Column(Date, nullable=False)
    # 股票代码
    stock_code = Column(String(10), nullable=True)
    # 股票名称
    stock_name = Column(String(100), nullable=True)
    # 持仓占比（%）
    holding_ratio = Column(Numeric(6, 2), nullable=True)
    # 持仓股数
    holding_shares = Column(Numeric(20, 2), nullable=True)
    # 持仓市值
    holding_value = Column(Numeric(20, 2), nullable=True)
    # 所属行业
    industry = Column(String(50), nullable=True)
    # 创建时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关联关系
    fund = relationship("Fund", back_populates="holdings")

    def __repr__(self):
        return f"<FundHolding {self.fund_code} {self.stock_code}>"


class FundFee(Base):
    """基金费率表"""
    __tablename__ = "fund_fees"

    # 主键，使用 String(36) 存储 UUID 字符串，兼容 SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 基金代码，外键关联 funds.fund_code
    fund_code = Column(String(6), ForeignKey("funds.fund_code", ondelete="CASCADE"), nullable=False, index=True)
    # 费率类型（如：申购费、赎回费）
    fee_type = Column(String(20), nullable=False)
    # 最短持有天数
    min_holding_days = Column(Integer, nullable=True)
    # 最长持有天数
    max_holding_days = Column(Integer, nullable=True)
    # 费率
    fee_rate = Column(Numeric(5, 4), nullable=False)
    # 是否有折扣
    is_discounted = Column(Boolean, nullable=False, default=False)
    # 折扣费率
    discount_rate = Column(Numeric(3, 2), nullable=True)
    # 创建时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # 更新时间
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    fund = relationship("Fund", back_populates="fees")

    def __repr__(self):
        return f"<FundFee {self.fund_code} {self.fee_type}>"
