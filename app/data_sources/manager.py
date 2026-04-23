"""
数据源管理器 - 管理多个数据源实例，实现自动切换和缓存机制
"""
import logging
import json
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from .base import BaseDataSource
from .tushare_adapter import TushareAdapter
from .akshare_adapter import AkshareAdapter
from app.core.redis_client import redis_client, CacheKeys, CacheExpire


logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    PRIMARY = "primary"
    BACKUP = "backup"


class DataSourceManager:
    """
    数据源管理器
    
    管理主数据源（Tushare）和备用数据源（Akshare），
    实现自动故障切换和数据缓存机制。
    """
    
    def __init__(self):
        """初始化数据源管理器"""
        # 初始化主数据源（Tushare）
        self._primary_source: Optional[BaseDataSource] = None
        # 初始化备用数据源（Akshare）
        self._backup_source: Optional[BaseDataSource] = None
        # 当前使用的数据源
        self._current_source_type: DataSourceType = DataSourceType.PRIMARY
        # Redis 客户端
        self._redis = None
        
        # 延迟初始化数据源实例
        self._initialized = False
        
        logger.info("数据源管理器创建完成")
    
    async def _ensure_initialized(self) -> None:
        """确保数据源已初始化"""
        if self._initialized:
            return
        
        try:
            # 初始化主数据源
            self._primary_source = TushareAdapter()
            logger.info(f"主数据源（Tushare）初始化完成，可用状态: {self._primary_source.is_available}")
            
            # 初始化备用数据源
            self._backup_source = AkshareAdapter()
            logger.info(f"备用数据源（Akshare）初始化完成，可用状态: {self._backup_source.is_available}")
            
            # 获取 Redis 客户端
            self._redis = await redis_client.get_client()
            
            # 如果主数据源不可用，自动切换到备用数据源
            if not self._primary_source.is_available and self._backup_source.is_available:
                self._current_source_type = DataSourceType.BACKUP
                logger.warning("主数据源不可用，已自动切换到备用数据源")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"数据源初始化失败: {e}")
            raise
    
    @property
    def current_source(self) -> Optional[BaseDataSource]:
        """获取当前使用的数据源"""
        if self._current_source_type == DataSourceType.PRIMARY:
            return self._primary_source
        return self._backup_source
    
    @property
    def current_source_name(self) -> str:
        """获取当前数据源名称"""
        source = self.current_source
        return source.name if source else "unknown"
    
    async def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，不存在则返回 None
        """
        try:
            cached = await self._redis.get(key)
            if cached:
                logger.debug(f"缓存命中: {key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
        return None
    
    async def _set_cache(self, key: str, data: Any, expire: int) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            expire: 过期时间（秒）
        """
        try:
            await self._redis.setex(key, expire, json.dumps(data, default=self._json_serializer))
            logger.debug(f"缓存已设置: {key}, 过期时间: {expire}秒")
        except Exception as e:
            logger.warning(f"设置缓存失败: {e}")
    
    def _json_serializer(self, obj):
        """JSON 序列化器，处理日期等特殊类型"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    async def _execute_with_fallback(
        self,
        method_name: str,
        *args,
        cache_key: Optional[str] = None,
        cache_expire: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        执行数据源方法，支持自动切换和缓存
        
        Args:
            method_name: 要执行的方法名
            cache_key: 缓存键
            cache_expire: 缓存过期时间
            *args, **kwargs: 方法参数
            
        Returns:
            方法执行结果
        """
        await self._ensure_initialized()
        
        # 尝试从缓存获取
        if cache_key:
            cached_result = await self._get_cache(cache_key)
            if cached_result is not None:
                return cached_result
        
        # 尝试使用当前数据源
        source = self.current_source
        if source and source.is_available:
            try:
                method = getattr(source, method_name)
                result = await method(*args, **kwargs)
                
                # 如果结果有效，缓存并返回
                if result is not None and cache_key and cache_expire:
                    await self._set_cache(cache_key, result, cache_expire)
                
                return result
                
            except Exception as e:
                logger.error(f"数据源 {source.name} 执行 {method_name} 失败: {e}")
        
        # 尝试切换到备用数据源
        other_source = None
        if self._current_source_type == DataSourceType.PRIMARY and self._backup_source:
            other_source = self._backup_source
            other_type = DataSourceType.BACKUP
        elif self._current_source_type == DataSourceType.BACKUP and self._primary_source:
            other_source = self._primary_source
            other_type = DataSourceType.PRIMARY
        
        if other_source and other_source.is_available:
            logger.info(f"尝试切换到 {'备用' if other_type == DataSourceType.BACKUP else '主'} 数据源")
            try:
                method = getattr(other_source, method_name)
                result = await method(*args, **kwargs)
                
                # 切换当前数据源
                self._current_source_type = other_type
                
                # 如果结果有效，缓存并返回
                if result is not None and cache_key and cache_expire:
                    await self._set_cache(cache_key, result, cache_expire)
                
                return result
                
            except Exception as e:
                logger.error(f"备用数据源 {other_source.name} 执行 {method_name} 也失败: {e}")
        
        logger.error(f"所有数据源都无法执行 {method_name}")
        return None
    
    async def get_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基础信息
        
        优先使用主数据源，失败时自动切换到备用数据源。
        缓存时间：24小时
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基础信息字典
        """
        cache_key = CacheKeys.FUND_INFO.format(fund_code=fund_code)
        
        result = await self._execute_with_fallback(
            "get_fund_info",
            fund_code,
            cache_key=cache_key,
            cache_expire=CacheExpire.FUND_INFO
        )
        
        if result:
            logger.info(f"获取基金 {fund_code} 信息成功，数据源: {self.current_source_name}")
        else:
            logger.warning(f"获取基金 {fund_code} 信息失败")
        
        return result
    
    async def search_funds(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索基金
        
        优先使用主数据源，失败时自动切换到备用数据源。
        搜索结果缓存5分钟（平衡实时性和性能）
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            匹配的基金列表
        """
        await self._ensure_initialized()
        
        # 搜索结果缓存键
        cache_key = f"fund:search:{keyword}:{limit}"
        cache_expire = 300  # 5分钟缓存
        
        # 尝试从缓存获取
        cached_result = await self._get_cache(cache_key)
        if cached_result is not None:
            logger.info(f"搜索基金 '{keyword}' 缓存命中，找到 {len(cached_result)} 条结果")
            return cached_result
        
        # 执行搜索
        result = await self._execute_with_fallback(
            "search_funds",
            keyword,
            limit,
            cache_key=cache_key,
            cache_expire=cache_expire
        )
        
        if result:
            logger.info(f"搜索基金 '{keyword}' 成功，找到 {len(result)} 条结果，数据源: {self.current_source_name}")
        else:
            logger.warning(f"搜索基金 '{keyword}' 失败")
        
        return result or []
    
    async def get_nav_history(
        self,
        fund_code: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取净值历史数据
        
        优先使用主数据源，失败时自动切换到备用数据源。
        缓存时间：1小时
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            净值历史数据列表
        """
        cache_key = CacheKeys.FUND_NAV_HISTORY.format(
            fund_code=fund_code,
            start=start_date.isoformat(),
            end=end_date.isoformat()
        )
        
        result = await self._execute_with_fallback(
            "get_nav_history",
            fund_code,
            start_date,
            end_date,
            cache_key=cache_key,
            cache_expire=CacheExpire.FUND_NAV_HISTORY
        )
        
        if result:
            logger.info(f"获取基金 {fund_code} 净值历史成功，共 {len(result)} 条记录，数据源: {self.current_source_name}")
        else:
            logger.warning(f"获取基金 {fund_code} 净值历史失败")
        
        return result or []
    
    async def get_holdings(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取持仓信息
        
        优先使用主数据源，失败时自动切换到备用数据源。
        缓存时间：7天
        
        Args:
            fund_code: 基金代码
            
        Returns:
            持仓信息字典
        """
        # 持仓信息缓存键使用基金代码（不包含报告日期，取最新）
        cache_key = f"fund:holdings:{fund_code}:latest"
        
        result = await self._execute_with_fallback(
            "get_holdings",
            fund_code,
            cache_key=cache_key,
            cache_expire=CacheExpire.FUND_HOLDINGS
        )
        
        if result:
            logger.info(f"获取基金 {fund_code} 持仓信息成功，数据源: {self.current_source_name}")
        else:
            logger.warning(f"获取基金 {fund_code} 持仓信息失败")
        
        return result
    
    async def get_fund_manager(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金经理信息
        
        优先使用主数据源，失败时自动切换到备用数据源。
        缓存时间：24小时
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金经理信息字典
        """
        cache_key = f"fund:manager:{fund_code}"
        
        result = await self._execute_with_fallback(
            "get_fund_manager",
            fund_code,
            cache_key=cache_key,
            cache_expire=CacheExpire.FUND_INFO  # 使用与基金信息相同的缓存时间
        )
        
        if result:
            logger.info(f"获取基金 {fund_code} 基金经理信息成功，数据源: {self.current_source_name}")
        else:
            logger.warning(f"获取基金 {fund_code} 基金经理信息失败")
        
        return result
    
    async def get_fund_fees(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取费率信息
        
        优先使用主数据源，失败时自动切换到备用数据源。
        缓存时间：30天
        
        Args:
            fund_code: 基金代码
            
        Returns:
            费率信息字典
        """
        cache_key = CacheKeys.FUND_FEES.format(fund_code=fund_code)
        
        result = await self._execute_with_fallback(
            "get_fund_fees",
            fund_code,
            cache_key=cache_key,
            cache_expire=CacheExpire.FUND_FEES
        )
        
        if result:
            logger.info(f"获取基金 {fund_code} 费率信息成功，数据源: {self.current_source_name}")
        else:
            logger.warning(f"获取基金 {fund_code} 费率信息失败")
        
        return result
    
    async def get_news_sentiment(self, fund_code: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        获取新闻舆情数据
        
        当前数据源暂不支持此功能，返回None由工具层提供占位数据
        
        Args:
            fund_code: 基金代码
            days: 获取最近N天的新闻
            
        Returns:
            新闻舆情数据字典
        """
        logger.info(f"获取基金 {fund_code} 新闻舆情数据（当前数据源暂不支持）")
        return None
    
    async def get_fund_flow(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取资金流向数据
        
        当前数据源暂不支持此功能，返回None由工具层提供占位数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            资金流向数据字典
        """
        logger.info(f"获取基金 {fund_code} 资金流向数据（当前数据源暂不支持）")
        return None
    
    async def get_social_heat(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取社交媒体热度数据
        
        当前数据源暂不支持此功能，返回None由工具层提供占位数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            社交媒体热度数据字典
        """
        logger.info(f"获取基金 {fund_code} 社交媒体热度数据（当前数据源暂不支持）")
        return None
    
    async def get_institutional_views(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取机构观点数据
        
        当前数据源暂不支持此功能，返回None由工具层提供占位数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            机构观点数据字典
        """
        logger.info(f"获取基金 {fund_code} 机构观点数据（当前数据源暂不支持）")
        return None

    async def check_health(self) -> Dict[str, Any]:
        """
        检查所有数据源健康状态
        
        Returns:
            包含各数据源健康状态的字典
        """
        await self._ensure_initialized()
        
        health_status = {
            "primary_source": {
                "name": "tushare",
                "available": False,
                "healthy": False
            },
            "backup_source": {
                "name": "akshare",
                "available": False,
                "healthy": False
            },
            "current_source": self.current_source_name,
            "redis_connected": False
        }
        
        # 检查 Redis 连接
        try:
            await self._redis.ping()
            health_status["redis_connected"] = True
        except Exception as e:
            logger.warning(f"Redis 连接检查失败: {e}")
        
        # 检查主数据源
        if self._primary_source:
            health_status["primary_source"]["available"] = self._primary_source.is_available
            if self._primary_source.is_available:
                try:
                    is_healthy = await self._primary_source.check_health()
                    health_status["primary_source"]["healthy"] = is_healthy
                except Exception as e:
                    logger.error(f"主数据源健康检查异常: {e}")
        
        # 检查备用数据源
        if self._backup_source:
            health_status["backup_source"]["available"] = self._backup_source.is_available
            if self._backup_source.is_available:
                try:
                    is_healthy = await self._backup_source.check_health()
                    health_status["backup_source"]["healthy"] = is_healthy
                except Exception as e:
                    logger.error(f"备用数据源健康检查异常: {e}")
        
        logger.info(f"数据源健康检查完成: {health_status}")
        return health_status
    
    async def switch_to_backup(self) -> bool:
        """
        手动切换到备用数据源
        
        Returns:
            切换是否成功
        """
        await self._ensure_initialized()
        
        if not self._backup_source or not self._backup_source.is_available:
            logger.error("备用数据源不可用，无法切换")
            return False
        
        self._current_source_type = DataSourceType.BACKUP
        logger.info("已手动切换到备用数据源（Akshare）")
        return True
    
    async def switch_to_primary(self) -> bool:
        """
        手动切换回主数据源
        
        Returns:
            切换是否成功
        """
        await self._ensure_initialized()
        
        if not self._primary_source or not self._primary_source.is_available:
            logger.error("主数据源不可用，无法切换")
            return False
        
        self._current_source_type = DataSourceType.PRIMARY
        logger.info("已手动切换回主数据源（Tushare）")
        return True
    
    async def invalidate_cache(self, fund_code: str, cache_type: str = "all") -> None:
        """
        清除指定基金的缓存
        
        Args:
            fund_code: 基金代码
            cache_type: 缓存类型，可选值: "info", "nav", "holdings", "fees", "all"
        """
        await self._ensure_initialized()
        
        keys_to_delete = []
        
        if cache_type in ("info", "all"):
            keys_to_delete.append(CacheKeys.FUND_INFO.format(fund_code=fund_code))
            keys_to_delete.append(f"fund:manager:{fund_code}")
        
        if cache_type in ("nav", "all"):
            # 删除所有净值历史缓存（使用模式匹配）
            pattern = f"fund:nav_history:{fund_code}:*"
            try:
                keys = await self._redis.keys(pattern)
                keys_to_delete.extend(keys)
            except Exception as e:
                logger.warning(f"获取净值缓存键失败: {e}")
        
        if cache_type in ("holdings", "all"):
            keys_to_delete.append(f"fund:holdings:{fund_code}:latest")
        
        if cache_type in ("fees", "all"):
            keys_to_delete.append(CacheKeys.FUND_FEES.format(fund_code=fund_code))
        
        if keys_to_delete:
            try:
                deleted = await self._redis.delete(*keys_to_delete)
                logger.info(f"已清除 {deleted} 个缓存键")
            except Exception as e:
                logger.error(f"清除缓存失败: {e}")


# 全局数据源管理器实例
datasource_manager = DataSourceManager()
