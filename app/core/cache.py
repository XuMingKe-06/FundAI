"""
基于文件系统的缓存模块，替代 Redis 缓存

每个缓存项存储为独立的 JSON 文件，包含值和过期时间。
支持异步操作和 TTL 过期机制。
使用 asyncio.Lock 保护写操作的并发安全，
并通过延迟索引保存减少磁盘 I/O。
"""
import asyncio
import fnmatch
import hashlib
import json
import os
import time
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

# 索引保存延迟时间（秒）
_INDEX_SAVE_DELAY = 1.0


class CacheClient:
    """基于文件系统的缓存客户端，提供与 Redis 类似的简化异步接口"""

    _instance: Optional["CacheClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._cache_dir: Path = Path(settings.CACHE_DIR)
        self._index_file: Path = self._cache_dir / "_index.json"
        self._index: dict = {}
        # 并发写保护锁
        self._write_lock = asyncio.Lock()
        # 延迟索引保存相关
        self._index_dirty: bool = False
        self._save_task: Optional[asyncio.Task] = None
        self._ensure_cache_dir()
        self._load_index()
        self._initialized = True

    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在"""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """从索引文件加载缓存键到文件名的映射"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        """保存索引文件（同步操作，由延迟机制或关闭时调用）"""
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False)

    @staticmethod
    def _key_to_filename(key: str) -> str:
        """将缓存键转换为安全的文件名（使用 MD5 哈希）"""
        return hashlib.md5(key.encode("utf-8")).hexdigest() + ".json"

    def _get_cache_file(self, key: str) -> Path:
        """获取缓存键对应的文件路径"""
        if key in self._index:
            return self._cache_dir / self._index[key]
        filename = self._key_to_filename(key)
        return self._cache_dir / filename

    def _read_entry(self, key: str) -> Optional[dict]:
        """读取缓存条目（同步操作）"""
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                entry = json.load(f)
            # 检查是否过期
            if entry.get("expire_at") and time.time() > entry["expire_at"]:
                os.remove(cache_file)
                self._index.pop(key, None)
                # 标记索引脏位，不立即保存
                self._index_dirty = True
                return None
            return entry
        except (json.JSONDecodeError, OSError):
            return None

    def _write_entry(self, key: str, value: str, expire: int = None) -> None:
        """写入缓存条目（同步操作）"""
        filename = self._key_to_filename(key)
        cache_file = self._cache_dir / filename
        entry = {
            "key": key,
            "value": value,
            "expire_at": time.time() + expire if expire else None,
            "created_at": time.time(),
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        self._index[key] = filename
        # 标记索引脏位，不立即保存
        self._index_dirty = True

    def _delete_entry(self, key: str) -> None:
        """删除缓存条目（同步操作）"""
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            os.remove(cache_file)
        self._index.pop(key, None)
        # 标记索引脏位，不立即保存
        self._index_dirty = True

    def _match_keys(self, pattern: str) -> List[str]:
        """按模式匹配获取键列表（同步操作）"""
        matched = []
        for key in list(self._index.keys()):
            if fnmatch.fnmatch(key, pattern):
                # 验证条目是否仍然有效
                entry = self._read_entry(key)
                if entry is not None:
                    matched.append(key)
        return matched

    def _schedule_index_save(self) -> None:
        """安排延迟保存索引，合并短时间内的多次写入"""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.ensure_future(self._delayed_save_index())

    async def _delayed_save_index(self) -> None:
        """延迟保存索引，等待 _INDEX_SAVE_DELAY 秒后执行，减少磁盘 I/O"""
        await asyncio.sleep(_INDEX_SAVE_DELAY)
        if self._index_dirty:
            await asyncio.to_thread(self._save_index)
            self._index_dirty = False

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值字符串，不存在或已过期则返回 None
        """
        entry = await asyncio.to_thread(self._read_entry, key)
        if entry is None:
            # 读取时可能因过期清理而标记了脏位，安排保存
            if self._index_dirty:
                self._schedule_index_save()
            return None
        return entry.get("value")

    async def set(self, key: str, value: str, expire: int = None) -> None:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），None 表示永不过期
        """
        async with self._write_lock:
            await asyncio.to_thread(self._write_entry, key, value, expire)
        self._schedule_index_save()

    async def delete(self, key: str) -> None:
        """删除缓存键

        Args:
            key: 要删除的缓存键
        """
        async with self._write_lock:
            await asyncio.to_thread(self._delete_entry, key)
        self._schedule_index_save()

    async def keys(self, pattern: str = "*") -> List[str]:
        """按模式匹配获取键列表，支持 * 通配符

        Args:
            pattern: 匹配模式，如 "fund_info_*"，默认 "*" 匹配所有键

        Returns:
            匹配的键名列表
        """
        result = await asyncio.to_thread(self._match_keys, pattern)
        # 匹配过程中可能清理了过期条目，安排保存
        if self._index_dirty:
            self._schedule_index_save()
        return result

    async def close(self) -> None:
        """关闭缓存，取消待执行的延迟保存并强制写入脏索引"""
        # 取消待执行的延迟保存任务
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        # 如果索引有未保存的变更，立即保存
        if self._index_dirty:
            await asyncio.to_thread(self._save_index)
            self._index_dirty = False

    async def ping(self) -> bool:
        """检查缓存是否可用

        Returns:
            True
        """
        return True


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
