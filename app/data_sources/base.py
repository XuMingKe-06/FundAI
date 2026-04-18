"""
数据源适配器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date


class BaseDataSource(ABC):
    """数据源适配器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_available = True
    
    @abstractmethod
    async def get_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金基础信息"""
        pass
    
    @abstractmethod
    async def search_funds(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索基金"""
        pass
    
    @abstractmethod
    async def get_nav_history(
        self,
        fund_code: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取净值历史"""
        pass
    
    @abstractmethod
    async def get_holdings(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取持仓信息"""
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """检查数据源健康状态"""
        pass
