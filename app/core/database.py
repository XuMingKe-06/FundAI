"""
数据库连接配置

使用 PostgreSQL 作为数据库，asyncpg 作为异步驱动。
支持连接池配置，提升并发读写性能。
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def utcnow() -> datetime:
    """返回当前 UTC 时间（不带时区信息）

    数据库列类型为 TIMESTAMP WITHOUT TIME ZONE，
    asyncpg 拒绝带 tzinfo 的 datetime，因此需要去除时区信息。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# 异步引擎（PostgreSQL + asyncpg）
# pool_size：连接池保持的连接数
# max_overflow：超出 pool_size 后允许的最大额外连接数
# echo=False：不使用 SQLAlchemy 自带的 echo 机制输出 SQL 日志，
# 而是由 logger.py 的 InterceptHandler 统一拦截 sqlalchemy.engine 日志，
# 避免控制台双输出，并确保 SQL 日志正确写入文件
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # 连接池预检测，自动回收断开的连接
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明基类（所有 ORM 模型继承此类）
class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncSession:
    """获取异步数据库会话，用于依赖注入"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
