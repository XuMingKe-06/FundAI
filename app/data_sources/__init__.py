"""
数据源模块初始化
"""
from app.data_sources.base import BaseDataSource
from app.data_sources.tushare_adapter import TushareAdapter
from app.data_sources.akshare_adapter import AkshareAdapter
from app.data_sources.manager import DataSourceManager, datasource_manager

__all__ = [
    "BaseDataSource",
    "TushareAdapter",
    "AkshareAdapter",
    "DataSourceManager",
    "datasource_manager",
]
