"""
基金数据获取工具

提供基金基础信息、净值历史、持仓、基金经理、费率等数据获取功能
"""
from typing import Dict, Any, Optional
from datetime import date, timedelta
import logging

from app.agents.tools.base import (
    BaseTool, 
    ToolResult, 
    ToolCategory,
    register_tool
)
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)


@register_tool
class GetFundInfoTool(BaseTool):
    """
    获取基金基础信息工具
    
    获取基金的基本信息，包括基金名称、类型、规模、成立日期等
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA
    
    @property
    def name(self) -> str:
        return "get_fund_info"
    
    @property
    def description(self) -> str:
        return "获取基金基础信息，包括基金名称、类型、规模、成立日期、管理人等"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字，如 '000001'"
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(self, fund_code: str) -> ToolResult:
        """
        执行获取基金基础信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含基金基础信息的 ToolResult
        """
        try:
            fund_info = await datasource_manager.get_fund_info(fund_code)
            
            if fund_info is None:
                return ToolResult.fail(
                    f"无法获取基金 {fund_code} 的基础信息",
                    metadata={"fund_code": fund_code}
                )
            
            return ToolResult.ok(
                data=fund_info,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取基金基础信息失败: {e}", exc_info=True)
            return ToolResult.fail(
                f"获取基金基础信息异常: {str(e)}",
                metadata={"fund_code": fund_code}
            )


@register_tool
class GetNavHistoryTool(BaseTool):
    """
    获取净值历史数据工具
    
    获取指定时间范围内的基金净值历史数据
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA
    
    @property
    def name(self) -> str:
        return "get_nav_history"
    
    @property
    def description(self) -> str:
        return "获取基金净值历史数据，包括单位净值、累计净值、涨跌幅等"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，6位数字"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 'YYYY-MM-DD'，不填则默认为一年前",
                    "format": "date"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 'YYYY-MM-DD'，不填则默认为今天",
                    "format": "date"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近N天的数据，与 start_date/end_date 二选一，默认365天"
                }
            },
            "required": ["fund_code"]
        }
    
    async def execute(
        self, 
        fund_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None
    ) -> ToolResult:
        """
        执行获取净值历史数据
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期字符串
            end_date: 结束日期字符串
            days: 最近天数
            
        Returns:
            包含净值历史数据的 ToolResult
        """
        try:
            if days:
                end = date.today()
                start = end - timedelta(days=days)
            else:
                end = date.fromisoformat(end_date) if end_date else date.today()
                start = date.fromisoformat(start_date) if start_date else end - timedelta(days=365)
            
            nav_history = await datasource_manager.get_nav_history(
                fund_code=fund_code,
                start_date=start,
                end_date=end
            )
            
            if not nav_history:
                return ToolResult.fail(
                    f"无法获取基金 {fund_code} 的净值历史数据",
                    metadata={
                        "fund_code": fund_code,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat()
                    }
                )
            
            return ToolResult.ok(
                data=nav_history,
                metadata={
                    "fund_code": fund_code,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "data_points": len(nav_history),
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取净值历史数据失败: {e}", exc_info=True)
            return ToolResult.fail(
                f"获取净值历史数据异常: {str(e)}",
                metadata={"fund_code": fund_code}
            )


@register_tool
class GetHoldingsTool(BaseTool):
    """
    获取持仓信息工具
    
    获取基金的最新持仓信息，包括股票持仓、债券持仓、行业分布等
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA
    
    @property
    def name(self) -> str:
        return "get_holdings"
    
    @property
    def description(self) -> str:
        return "获取基金持仓信息，包括股票持仓、债券持仓、行业分布、前十大重仓股等"
    
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
        执行获取持仓信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含持仓信息的 ToolResult
        """
        try:
            holdings = await datasource_manager.get_holdings(fund_code)
            
            if holdings is None:
                return ToolResult.fail(
                    f"无法获取基金 {fund_code} 的持仓信息",
                    metadata={"fund_code": fund_code}
                )
            
            return ToolResult.ok(
                data=holdings,
                metadata={
                    "fund_code": fund_code,
                    "report_date": holdings.get("report_date"),
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}", exc_info=True)
            return ToolResult.fail(
                f"获取持仓信息异常: {str(e)}",
                metadata={"fund_code": fund_code}
            )


@register_tool
class GetFundManagerTool(BaseTool):
    """
    获取基金经理信息工具
    
    获取基金经理的基本信息和历史业绩
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA
    
    @property
    def name(self) -> str:
        return "get_fund_manager"
    
    @property
    def description(self) -> str:
        return "获取基金经理信息，包括姓名、从业年限、管理基金数量、历史业绩等"
    
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
        执行获取基金经理信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含基金经理信息的 ToolResult
        """
        try:
            manager_info = await datasource_manager.get_fund_manager(fund_code)
            
            if manager_info is None:
                return ToolResult.fail(
                    f"无法获取基金 {fund_code} 的基金经理信息",
                    metadata={"fund_code": fund_code}
                )
            
            return ToolResult.ok(
                data=manager_info,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取基金经理信息失败: {e}", exc_info=True)
            return ToolResult.fail(
                f"获取基金经理信息异常: {str(e)}",
                metadata={"fund_code": fund_code}
            )


@register_tool
class GetFundFeesTool(BaseTool):
    """
    获取费率信息工具
    
    获取基金的申购费率、赎回费率、管理费等费用信息
    """
    
    def __init__(self):
        super().__init__()
        self._category = ToolCategory.FUND_DATA
    
    @property
    def name(self) -> str:
        return "get_fund_fees"
    
    @property
    def description(self) -> str:
        return "获取基金费率信息，包括申购费率、赎回费率、管理费、托管费等"
    
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
        执行获取费率信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含费率信息的 ToolResult
        """
        try:
            fees_info = await datasource_manager.get_fund_fees(fund_code)
            
            if fees_info is None:
                return ToolResult.fail(
                    f"无法获取基金 {fund_code} 的费率信息",
                    metadata={"fund_code": fund_code}
                )
            
            return ToolResult.ok(
                data=fees_info,
                metadata={
                    "fund_code": fund_code,
                    "data_source": datasource_manager.current_source_name
                }
            )
            
        except Exception as e:
            logger.error(f"获取费率信息失败: {e}", exc_info=True)
            return ToolResult.fail(
                f"获取费率信息异常: {str(e)}",
                metadata={"fund_code": fund_code}
            )
