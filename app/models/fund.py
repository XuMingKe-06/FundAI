"""
基金模型
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, Date, Numeric, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Fund(Base):
    """基金基础信息表"""
    __tablename__ = "funds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    fund_name = Column(String(200), nullable=False)
    fund_type = Column(String(50), nullable=False)
    fund_manager = Column(String(100), nullable=True)
    establish_date = Column(Date, nullable=False)
    management_fee = Column(Numeric(5, 4), nullable=True)
    custody_fee = Column(Numeric(5, 4), nullable=True)
    current_scale = Column(Numeric(20, 2), nullable=True)
    purchase_status = Column(String(20), nullable=False, default="normal")
    redemption_status = Column(String(20), nullable=False, default="normal")
    benchmark = Column(String(200), nullable=True)
    is_qdii = Column(Boolean, nullable=False, default=False)
    share_class = Column(String(1), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
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
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code = Column(String(6), nullable=False, index=True)
    nav_date = Column(Date, nullable=False)
    unit_nav = Column(Numeric(10, 4), nullable=False)
    accumulated_nav = Column(Numeric(10, 4), nullable=False)
    daily_growth_rate = Column(Numeric(8, 4), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 联合唯一约束
    __table_args__ = (
        {"unique_constraint": ("fund_code", "nav_date")},
    )
    
    # 关联关系
    fund = relationship("Fund", back_populates="nav_history")
    
    def __repr__(self):
        return f"<FundNav {self.fund_code} {self.nav_date}: {self.unit_nav}>"


class FundHolding(Base):
    """基金持仓表"""
    __tablename__ = "fund_holdings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code = Column(String(6), nullable=False, index=True)
    report_date = Column(Date, nullable=False)
    stock_code = Column(String(10), nullable=True)
    stock_name = Column(String(100), nullable=True)
    holding_ratio = Column(Numeric(6, 2), nullable=True)
    holding_shares = Column(Numeric(20, 2), nullable=True)
    holding_value = Column(Numeric(20, 2), nullable=True)
    industry = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关联关系
    fund = relationship("Fund", back_populates="holdings")
    
    def __repr__(self):
        return f"<FundHolding {self.fund_code} {self.stock_code}>"


class FundFee(Base):
    """基金费率表"""
    __tablename__ = "fund_fees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code = Column(String(6), nullable=False, index=True)
    fee_type = Column(String(20), nullable=False)
    min_holding_days = Column(Integer, nullable=True)
    max_holding_days = Column(Integer, nullable=True)
    fee_rate = Column(Numeric(5, 4), nullable=False)
    is_discounted = Column(Boolean, nullable=False, default=False)
    discount_rate = Column(Numeric(3, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    fund = relationship("Fund", back_populates="fees")
    
    def __repr__(self):
        return f"<FundFee {self.fund_code} {self.fee_type}>"
