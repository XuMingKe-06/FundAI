"""
Redis连接配置
"""
import redis.asyncio as redis
from typing import Optional

from app.core.config import settings


class RedisClient:
    """Redis客户端管理类"""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局Redis客户端实例
redis_client = RedisClient()


async def get_redis() -> redis.Redis:
    """获取Redis客户端依赖"""
    return await redis_client.get_client()


# 缓存键命名规范
class CacheKeys:
    """缓存键常量"""
    
    # 基金信息缓存
    FUND_INFO = "fund:info:{fund_code}"
    FUND_NAV = "fund:nav:{fund_code}:{date}"
    FUND_NAV_HISTORY = "fund:nav_history:{fund_code}:{start}:{end}"
    FUND_HOLDINGS = "fund:holdings:{fund_code}:{report_date}"
    FUND_FEES = "fund:fees:{fund_code}"
    
    # 用户会话缓存
    SESSION = "session:{session_id}"
    USER_PREFERENCE = "user:preference:{user_id}"
    
    # 分析结果缓存
    ANALYSIS_RESULT = "analysis:result:{session_id}"
    
    # 智能体状态缓存
    AGENT_STATUS = "agent:status:{session_id}:{agent_type}"
    
    # 数据源状态
    DATASOURCE_HEALTH = "datasource:health:{source_name}"
    
    # 限流键
    RATELIMIT = "ratelimit:{user_id}:{endpoint}"
    
    # 验证码
    VERIFY_CODE = "verify:code:{phone}:{type}"
    
    # JWT黑名单
    JWT_BLACKLIST = "jwt:blacklist:{token_jti}"


# 缓存过期时间（秒）
class CacheExpire:
    """缓存过期时间常量"""
    
    FUND_INFO = 86400  # 24小时
    FUND_NAV = 3600  # 1小时
    FUND_NAV_HISTORY = 3600  # 1小时
    FUND_HOLDINGS = 604800  # 7天
    FUND_FEES = 2592000  # 30天
    SESSION = 2592000  # 30天
    USER_PREFERENCE = 604800  # 7天
    AGENT_STATUS = 3600  # 1小时
    VERIFY_CODE = 300  # 5分钟
    JWT_BLACKLIST = 604800  # 7天
