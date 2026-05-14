"""
配置管理模块

管理 data/config.json 配置文件，支持嵌套键访问、线程安全的单例模式。
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings

# 默认配置结构
DEFAULT_CONFIG: Dict[str, Any] = {
    "llm": {
        "api_base_url": "",
        "api_key": "",
        "model": "",
        "embedding_api_base_url": "",
        "embedding_api_key": "",
        "embedding_model": "",
    },
    "datasource": {
        "tushare_token": "",
    },
    "rag": {
        "embedding_mode": "api",
        "top_k": 5,
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
}


class SettingsManager:
    """
    配置管理器

    负责从 JSON 文件加载/保存配置，支持点号分隔的嵌套键访问。
    使用线程锁保证并发安全，采用单例模式全局复用。
    """

    _instance: Optional["SettingsManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "SettingsManager":
        """单例模式：确保全局只创建一个实例"""
        if cls._instance is None:
            with cls._lock:
                # 双重检查，防止多线程下重复创建
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化配置管理器（仅首次创建时执行）"""
        if self._initialized:
            return
        self._config_path: Path = Path(settings.CONFIG_FILE)
        self._data: Dict[str, Any] = {}
        self._file_lock: threading.RLock = threading.RLock()
        self._load()
        self._initialized = True

    def _load(self) -> None:
        """
        从 JSON 文件加载配置

        如果配置文件不存在，则创建默认配置并写入文件。
        如果文件存在但解析失败，则回退到默认配置。
        """
        with self._file_lock:
            if self._config_path.exists():
                try:
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._data = json.load(f)
                    # 将默认配置中缺失的键合并进来
                    self._data = self._deep_merge(self._deep_copy(DEFAULT_CONFIG), self._data)
                except (json.JSONDecodeError, OSError):
                    # 文件损坏或读取失败时使用默认配置
                    self._data = self._deep_copy(DEFAULT_CONFIG)
            else:
                # 文件不存在，创建默认配置
                self._data = self._deep_copy(DEFAULT_CONFIG)
                self.ensure_data_dir()
                self._save()

    def _save(self) -> None:
        """将当前配置保存到 JSON 文件"""
        with self._file_lock:
            self.ensure_data_dir()
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键

        示例:
            get("llm.api_key")  -> 访问 self._data["llm"]["api_key"]
            get("rag.top_k", 3) -> 如果键不存在则返回默认值 3

        Args:
            key: 点号分隔的配置键
            default: 键不存在时的默认返回值

        Returns:
            配置值，键不存在时返回 default
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值，支持点号分隔的嵌套键

        如果中间层级的键不存在，会自动创建空字典。

        示例:
            set("llm.api_key", "sk-xxx")
            set("rag.top_k", 10)

        Args:
            key: 点号分隔的配置键
            value: 要设置的值
        """
        keys = key.split(".")
        target = self._data
        # 逐层深入，缺失的中间键自动创建为空字典
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置的深拷贝

        Returns:
            配置字典的深拷贝，避免外部修改影响内部数据
        """
        return self._deep_copy(self._data)

    def update(self, data: Dict[str, Any]) -> None:
        """
        批量更新配置

        将传入的字典深度合并到现有配置中，然后保存到文件。

        Args:
            data: 要合并的配置字典
        """
        self._data = self._deep_merge(self._data, data)
        self._save()

    def ensure_data_dir(self) -> None:
        """确保配置文件所在的目录存在，不存在则递归创建"""
        dir_path = self._config_path.parent
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典

        override 中的值会覆盖 base 中的同名键。
        如果两个键对应的值都是字典，则递归合并。

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = SettingsManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _deep_copy(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        深拷贝字典

        使用 JSON 序列化/反序列化实现，确保所有嵌套结构都被复制。

        Args:
            data: 要拷贝的字典

        Returns:
            深拷贝后的字典
        """
        return json.loads(json.dumps(data))

    def is_embedding_configured(self) -> bool:
        """
        检查 Embedding 是否已配置

        需要同时满足以下三个条件：
        1. embedding_api_base_url 不为空
        2. embedding_api_key 不为空
        3. embedding_model 不为空

        Returns:
            True 表示已配置，False 表示未配置
        """
        api_base_url = self.get("llm.embedding_api_base_url", "")
        api_key = self.get("llm.embedding_api_key", "")
        model = self.get("llm.embedding_model", "")

        return bool(api_base_url and api_key and model)


# 全局单例实例（延迟初始化）
settings_manager: Optional["SettingsManager"] = None


def get_settings_manager() -> "SettingsManager":
    """获取配置管理器单例（延迟初始化）"""
    global settings_manager
    if settings_manager is None:
        settings_manager = SettingsManager()
    return settings_manager
