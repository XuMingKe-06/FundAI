"""
市场数据获取工具

提供新闻舆情、资金流向、市场热度等市场数据获取工具
"""
from typing import Dict, Any, List
import logging
import asyncio

from app.agents.tools.base import (
    BaseTool, 
    ToolResult, 
    ToolCategory, 
    register_tool
)
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)


@register_tool
class GetNewsSentimentTool(BaseTool):
    """
    获取新闻舆情数据工具
    
    获取基金相关的新闻舆情分析数据
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.MARKET_DATA
    
    @property
    def name(self) -> str:
        return "get_news_sentiment"
    
    @property
    def description(self) -> str:
        return "获取基金相关新闻舆情数据，包括正面、负面、中性新闻数量及情感分析"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近N天的新闻，默认30天",
                    "default": 30
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(self, fund_code: str, days: int = 30) -> ToolResult:
        """
        执行新闻舆情获取
        
        Args:
            fund_code: 基金代码
            days: 天数
            
        Returns:
            新闻舆情数据
        """
        try:
            news_data = await datasource_manager.get_news_sentiment(fund_code, days)
            
            if news_data is None:
                return ToolResult.ok(
                    data={
                        "total": 0,
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0,
                        "sentiment_score": 0.0,
                        "key_news": [],
                        "note": "暂无新闻数据"
                    }
                )
            
            return ToolResult.ok(
                data=news_data,
                metadata={
                    "fund_code": fund_code,
                    "days": days,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取新闻舆情失败: {e}", exc_info=True)
            return ToolResult.fail(f"获取新闻舆情异常: {str(e)}")


@register_tool
class GetFundFlowTool(BaseTool):
    """
    获取资金流向数据工具
    
    获取基金或相关板块的资金流向数据
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.MARKET_DATA
    
    @property
    def name(self) -> str:
        return "get_fund_flow"
    
    @property
    def description(self) -> str:
        return "获取资金流向数据，包括近5日、近20日净流入流出情况"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字"
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(self, fund_code: str) -> ToolResult:
        """
        执行资金流向获取
        
        Args:
            fund_code: 基金代码
            
        Returns:
            资金流向数据
        """
        try:
            flow_data = await datasource_manager.get_fund_flow(fund_code)
            
            if flow_data is None:
                return ToolResult.ok(
                    data={
                        "net_inflow_5d": 0.0,
                        "net_inflow_20d": 0.0,
                        "trend": "未知",
                        "note": "暂无资金流向数据"
                    }
                )
            
            return ToolResult.ok(
                data=flow_data,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}", exc_info=True)
            return ToolResult.fail(f"获取资金流向异常: {str(e)}")


@register_tool
class GetSocialHeatTool(BaseTool):
    """
    获取社交媒体热度工具
    
    获取基金在社交媒体上的讨论热度
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.MARKET_DATA
    
    @property
    def name(self) -> str:
        return "get_social_heat"
    
    @property
    def description(self) -> str:
        return "获取社交媒体热度数据，包括热度比率、讨论趋势等"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字"
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(self, fund_code: str) -> ToolResult:
        """
        执行社交媒体热度获取
        
        Args:
            fund_code: 基金代码
            
        Returns:
            社交媒体热度数据
        """
        try:
            heat_data = await datasource_manager.get_social_heat(fund_code)
            
            if heat_data is None:
                return ToolResult.ok(
                    data={
                        "heat_ratio": 1.0,
                        "level": "medium",
                        "trend": "平稳",
                        "note": "暂无社交媒体热度数据"
                    }
                )
            
            return ToolResult.ok(
                data=heat_data,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取社交媒体热度失败: {e}", exc_info=True)
            return ToolResult.fail(f"获取社交媒体热度异常: {str(e)}")


@register_tool
class GetInstitutionalViewsTool(BaseTool):
    """
    获取机构观点工具
    
    获取机构对基金或相关板块的研究观点
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.MARKET_DATA
    
    @property
    def name(self) -> str:
        return "get_institutional_views"
    
    @property
    def description(self) -> str:
        return "获取机构观点数据，包括买入、增持、中性、减持、卖出评级统计"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字"
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(self, fund_code: str) -> ToolResult:
        """
        执行机构观点获取
        
        Args:
            fund_code: 基金代码
            
        Returns:
            机构观点数据
        """
        try:
            views_data = await datasource_manager.get_institutional_views(fund_code)
            
            if views_data is None:
                return ToolResult.ok(
                    data={
                        "buy": 0,
                        "overweight": 0,
                        "neutral": 0,
                        "underweight": 0,
                        "sell": 0,
                        "total_reports": 0,
                        "consensus": "中性",
                        "note": "暂无机构观点数据"
                    }
                )
            
            return ToolResult.ok(
                data=views_data,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取机构观点失败: {e}", exc_info=True)
            return ToolResult.fail(f"获取机构观点异常: {str(e)}")


@register_tool
class GetMarketIndexTool(BaseTool):
    """
    获取市场指数数据工具
    
    获取主要市场指数的行情数据
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.MARKET_DATA
    
    @property
    def name(self) -> str:
        return "get_market_index"
    
    @property
    def description(self) -> str:
        return "获取市场指数数据，支持沪深300、上证指数、深证成指等主要指数"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "index_code": {
                    "type": "string",
                    "description": "指数代码，如 '000300'（沪深300）、'000001'（上证指数）",
                    "enum": ["000300", "000001", "399001", "000016", "000905", "000852"]
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近N天的数据，默认30天",
                    "default": 30
                }
            },
            "required": ["index_code"]
        }
    
    async def execute(self, index_code: str, days: int = 30) -> ToolResult:
        """
        执行市场指数获取
        
        Args:
            index_code: 指数代码
            days: 天数
            
        Returns:
            市场指数数据
        """
        try:
            from datetime import date, timedelta
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            index_data = await datasource_manager.get_nav_history(
                index_code, start_date, end_date
            )
            
            if not index_data:
                return ToolResult.ok(
                    data={
                        "index_code": index_code,
                        "index_name": self._get_index_name(index_code),
                        "data": [],
                        "note": "暂无指数数据"
                    }
                )
            
            return ToolResult.ok(
                data={
                    "index_code": index_code,
                    "index_name": self._get_index_name(index_code),
                    "data": index_data,
                    "data_points": len(index_data)
                },
                metadata={
                    "index_code": index_code,
                    "days": days,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取市场指数失败: {e}", exc_info=True)
            return ToolResult.fail(f"获取市场指数异常: {str(e)}")
    
    def _get_index_name(self, index_code: str) -> str:
        """获取指数名称"""
        index_names = {
            "000300": "沪深300",
            "000001": "上证指数",
            "399001": "深证成指",
            "000016": "上证50",
            "000905": "中证500",
            "000852": "中证1000"
        }
        return index_names.get(index_code, "未知指数")
