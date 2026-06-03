"""
数据库连接配置

使用 SQLite 作为数据库，aiosqlite 作为异步驱动。
数据库文件位于 data/fundai.db，运行时自动创建 data 目录。
启用 WAL 模式以提升并发读写性能。
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.core.config import settings

# 确保数据目录存在（SQLite 数据库文件需要所在目录已存在）
os.makedirs("data", exist_ok=True)

# 异步引擎（SQLite + aiosqlite）
# SQLite 不支持连接池参数（pool_size / max_overflow），因此移除
# check_same_thread=False 允许跨线程使用同一连接（异步场景必需）
# echo=False：不使用 SQLAlchemy 自带的 echo 机制输出 SQL 日志，
# 而是由 logger.py 的 InterceptHandler 统一拦截 sqlalchemy.engine 日志，
# 避免控制台双输出，并确保 SQL 日志正确写入文件
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# 通过事件监听器启用 SQLite WAL 模式和外键约束
# WAL 模式无法通过 connect_args 设置，必须通过 PRAGMA 语句启用
# WAL 模式优势：读写不互斥，大幅提升并发读性能
@event.listens_for(async_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
