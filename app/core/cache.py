"""
Redis 缓存模块

基于 redis.asyncio 的异步缓存客户端，提供与之前文件缓存相同的接口。
支持 TTL 过期机制和模式匹配键查询。
"""
from typing import List, Optional

import redis.asyncio as aioredis

from app.core.config import settings


class CacheClient:
    """基于 Redis 的缓存客户端，提供简化的异步接口"""

    _instance: Optional["CacheClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Redis 异步客户端（延迟连接，首次操作时建立）
        self._redis: Optional[aioredis.Redis] = None
        self._initialized = True

    async def _ensure_connection(self) -> aioredis.Redis:
        """确保 Redis 连接已建立"""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,  # 自动将 bytes 解码为 str
                max_connections=10,
                protocol=2,  # 强制使用 RESP2 协议，兼容不支持 HELLO 命令的旧版 Redis 服务器
            )
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值字符串，不存在则返回 None
        """
        redis = await self._ensure_connection()
        return await redis.get(key)

    async def set(self, key: str, value: str, expire: int = None) -> None:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），None 表示永不过期
        """
        redis = await self._ensure_connection()
        if expire:
            await redis.setex(key, expire, value)
        else:
            await redis.set(key, value)

    async def delete(self, key: str) -> None:
        """删除缓存键

        Args:
            key: 要删除的缓存键
        """
        redis = await self._ensure_connection()
        await redis.delete(key)

    async def keys(self, pattern: str = "*") -> List[str]:
        """按模式匹配获取键列表，支持 * 通配符

        Args:
            pattern: 匹配模式，如 "fund_info_*"，默认 "*" 匹配所有键

        Returns:
            匹配的键名列表
        """
        redis = await self._ensure_connection()
        return await redis.keys(pattern)

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def ping(self) -> bool:
        """检查 Redis 连接是否可用

        Returns:
            连接正常返回 True，否则抛出异常
        """
        redis = await self._ensure_connection()
        return await redis.ping()


# 全局缓存客户端实例
cache_client = CacheClient()


async def get_cache() -> CacheClient:
    """获取缓存客户端依赖注入函数"""
    return cache_client


# 缓存键命名规范（下划线分隔）
class CacheKeys:
    """缓存键常量"""

    # 基金信息缓存
    FUND_INFO = "fund_info_{fund_code}"
    FUND_NAV = "fund_nav_{fund_code}_{date}"
    FUND_NAV_HISTORY = "fund_nav_history_{fund_code}_{start}_{end}"
    FUND_HOLDINGS = "fund_holdings_{fund_code}_{report_date}"
    FUND_FEES = "fund_fees_{fund_code}"

    # 分析结果缓存
    ANALYSIS_RESULT = "analysis_result_{session_id}"

    # 智能体状态缓存
    AGENT_STATUS = "agent_status_{session_id}_{agent_type}"

    # 数据源状态
    DATASOURCE_HEALTH = "datasource_health_{source_name}"


# 缓存过期时间（秒）
class CacheExpire:
    """缓存过期时间常量"""

    FUND_INFO = 86400       # 24小时
    FUND_NAV = 3600         # 1小时
    FUND_NAV_HISTORY = 3600 # 1小时
    FUND_HOLDINGS = 604800  # 7天
    FUND_FEES = 2592000     # 30天
    ANALYSIS_RESULT = 86400 # 24小时
    AGENT_STATUS = 3600     # 1小时
    DATASOURCE_HEALTH = 300 # 5分钟
