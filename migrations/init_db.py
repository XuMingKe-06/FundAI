"""
数据库初始化脚本
"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

from sqlalchemy import select
from app.core.database import async_engine, AsyncSessionLocal, Base
from app.models.user import User, UserSettings
from app.models.fund import Fund, FundNav, FundHolding, FundFee
from app.core.security import get_password_hash


async def create_tables():
    """创建数据库表"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成")


async def seed_users(session):
    """创建测试用户"""
    # 创建测试用户
    salt = "test_salt_12345678"
    password_hash = get_password_hash("password123" + salt)
    
    test_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        phone="13800138000",
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        salt=salt,
        role="investor",
        risk_preference="neutral",
        is_active=True
    )
    session.add(test_user)
    
    # 创建管理员用户
    admin_salt = "admin_salt_12345678"
    admin_password_hash = get_password_hash("admin123" + admin_salt)
    
    admin_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        phone="13900139000",
        username="admin",
        email="admin@example.com",
        password_hash=admin_password_hash,
        salt=admin_salt,
        role="admin",
        risk_preference="neutral",
        is_active=True
    )
    session.add(admin_user)
    
    await session.commit()
    print("测试用户创建完成")


async def seed_funds(session):
    """创建测试基金数据"""
    funds_data = [
        {
            "fund_code": "000001",
            "fund_name": "华夏成长混合",
            "fund_type": "mixed",
            "fund_manager": "王某某",
            "establish_date": date(2001, 12, 18),
            "management_fee": Decimal("0.0150"),
            "custody_fee": Decimal("0.0025"),
            "current_scale": Decimal("8560000000.00"),
            "purchase_status": "normal",
            "redemption_status": "normal",
            "benchmark": "沪深300指数收益率*80%+中证全债指数收益率*20%",
            "is_qdii": False,
            "share_class": "A"
        },
        {
            "fund_code": "110022",
            "fund_name": "易方达消费行业",
            "fund_type": "stock",
            "fund_manager": "张某某",
            "establish_date": date(2010, 8, 20),
            "management_fee": Decimal("0.0150"),
            "custody_fee": Decimal("0.0025"),
            "current_scale": Decimal("3280000000.00"),
            "purchase_status": "normal",
            "redemption_status": "normal",
            "benchmark": "中证消费指数收益率*80%+中证全债指数收益率*20%",
            "is_qdii": False,
            "share_class": "A"
        },
        {
            "fund_code": "161725",
            "fund_name": "招商中证白酒",
            "fund_type": "index",
            "fund_manager": "李某某",
            "establish_date": date(2015, 5, 27),
            "management_fee": Decimal("0.0075"),
            "custody_fee": Decimal("0.0020"),
            "current_scale": Decimal("5680000000.00"),
            "purchase_status": "normal",
            "redemption_status": "normal",
            "benchmark": "中证白酒指数收益率*95%+银行活期存款利率*5%",
            "is_qdii": False,
            "share_class": None
        },
        {
            "fund_code": "519778",
            "fund_name": "交银定期支付双息",
            "fund_type": "bond",
            "fund_manager": "赵某某",
            "establish_date": date(2013, 6, 5),
            "management_fee": Decimal("0.0060"),
            "custody_fee": Decimal("0.0015"),
            "current_scale": Decimal("1250000000.00"),
            "purchase_status": "normal",
            "redemption_status": "normal",
            "benchmark": "中证全债指数收益率",
            "is_qdii": False,
            "share_class": "A"
        }
    ]
    
    for fund_data in funds_data:
        fund = Fund(**fund_data)
        session.add(fund)
    
    await session.commit()
    print("测试基金数据创建完成")


async def seed_nav_history(session):
    """创建净值历史数据"""
    # 为000001创建近3个月的净值数据
    base_nav = Decimal("1.2500")
    base_date = date.today() - timedelta(days=90)
    
    for i in range(90):
        nav_date = base_date + timedelta(days=i)
        # 模拟净值波动
        change = Decimal(str((i % 10 - 5) * 0.002))
        unit_nav = base_nav + change + Decimal(str(i * 0.001))
        accumulated_nav = unit_nav + Decimal("1.0")
        daily_growth_rate = change / base_nav if i > 0 else None
        
        nav = FundNav(
            fund_code="000001",
            nav_date=nav_date,
            unit_nav=unit_nav,
            accumulated_nav=accumulated_nav,
            daily_growth_rate=daily_growth_rate
        )
        session.add(nav)
    
    await session.commit()
    print("净值历史数据创建完成")


async def seed_holdings(session):
    """创建持仓数据"""
    holdings_data = [
        {
            "fund_code": "000001",
            "report_date": date(2026, 3, 31),
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "holding_ratio": Decimal("8.56"),
            "holding_value": Decimal("732000000.00"),
            "industry": "食品饮料"
        },
        {
            "fund_code": "000001",
            "report_date": date(2026, 3, 31),
            "stock_code": "000858",
            "stock_name": "五粮液",
            "holding_ratio": Decimal("6.23"),
            "holding_value": Decimal("533000000.00"),
            "industry": "食品饮料"
        },
        {
            "fund_code": "000001",
            "report_date": date(2026, 3, 31),
            "stock_code": "000333",
            "stock_name": "美的集团",
            "holding_ratio": Decimal("5.12"),
            "holding_value": Decimal("438000000.00"),
            "industry": "家用电器"
        },
        {
            "fund_code": "000001",
            "report_date": date(2026, 3, 31),
            "stock_code": "002475",
            "stock_name": "立讯精密",
            "holding_ratio": Decimal("4.85"),
            "holding_value": Decimal("415000000.00"),
            "industry": "电子"
        },
        {
            "fund_code": "000001",
            "report_date": date(2026, 3, 31),
            "stock_code": "300750",
            "stock_name": "宁德时代",
            "holding_ratio": Decimal("4.32"),
            "holding_value": Decimal("370000000.00"),
            "industry": "电气设备"
        }
    ]
    
    for holding_data in holdings_data:
        holding = FundHolding(**holding_data)
        session.add(holding)
    
    await session.commit()
    print("持仓数据创建完成")


async def seed_fees(session):
    """创建费率数据"""
    fees_data = [
        {
            "fund_code": "000001",
            "fee_type": "purchase",
            "fee_rate": Decimal("0.0150"),
            "is_discounted": True,
            "discount_rate": Decimal("0.10")
        },
        {
            "fund_code": "000001",
            "fee_type": "redemption",
            "min_holding_days": 0,
            "max_holding_days": 7,
            "fee_rate": Decimal("0.0150")
        },
        {
            "fund_code": "000001",
            "fee_type": "redemption",
            "min_holding_days": 7,
            "max_holding_days": 30,
            "fee_rate": Decimal("0.0075")
        },
        {
            "fund_code": "000001",
            "fee_type": "redemption",
            "min_holding_days": 30,
            "max_holding_days": 365,
            "fee_rate": Decimal("0.0050")
        },
        {
            "fund_code": "000001",
            "fee_type": "redemption",
            "min_holding_days": 365,
            "max_holding_days": 730,
            "fee_rate": Decimal("0.0025")
        },
        {
            "fund_code": "000001",
            "fee_type": "redemption",
            "min_holding_days": 730,
            "max_holding_days": None,
            "fee_rate": Decimal("0.0000")
        }
    ]
    
    for fee_data in fees_data:
        fee = FundFee(**fee_data)
        session.add(fee)
    
    await session.commit()
    print("费率数据创建完成")


async def main():
    """主函数"""
    print("开始初始化数据库...")
    
    # 创建表
    await create_tables()
    
    # 创建种子数据
    async with AsyncSessionLocal() as session:
        await seed_users(session)
        await seed_funds(session)
        await seed_nav_history(session)
        await seed_holdings(session)
        await seed_fees(session)
    
    print("数据库初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
