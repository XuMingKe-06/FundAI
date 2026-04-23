"""
工具基类和注册机制

定义工具的抽象基类、注册表和执行结果数据类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Type, Callable
from datetime import date, datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别枚举"""
    FUND_DATA = "fund_data"
    TECHNICAL_INDICATOR = "technical_indicator"
    RISK_METRIC = "risk_metric"
    MARKET_DATA = "market_data"


@dataclass
class ToolResult:
    """
    工具执行结果数据类
    
    封装工具执行的返回结果，包含状态、数据和错误信息
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def _serialize_value(obj: Any) -> Any:
        """递归序列化值，将 date/datetime 对象转换为 ISO 格式字符串"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: ToolResult._serialize_value(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ToolResult._serialize_value(item) for item in obj]
        return obj

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，自动将 date/datetime 对象转换为字符串"""
        return {
            "success": self.success,
            "data": self._serialize_value(self.data),
            "error": self.error,
            "metadata": self._serialize_value(self.metadata)
        }
    
    @classmethod
    def ok(cls, data: Any, metadata: Dict[str, Any] = None) -> "ToolResult":
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {}
        )
    
    @classmethod
    def fail(cls, error: str, metadata: Dict[str, Any] = None) -> "ToolResult":
        """创建失败结果"""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {}
        )


class BaseTool(ABC):
    """
    工具抽象基类
    
    所有工具必须继承此类并实现 execute 方法
    """
    
    def __init__(self):
        self._category: ToolCategory = ToolCategory.FUND_DATA
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """
        工具参数的 JSON Schema
        
        定义工具接受的参数结构，用于参数验证和文档生成
        """
        pass
    
    @property
    def category(self) -> ToolCategory:
        """工具类别"""
        return self._category
    
    @property
    def required_parameters(self) -> List[str]:
        """必需参数列表"""
        return self.parameters_schema.get("required", [])
    
    def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
        """
        验证参数是否有效
        
        Args:
            params: 参数字典
            
        Returns:
            错误信息，验证通过返回 None
        """
        required = self.required_parameters
        for param_name in required:
            if param_name not in params or params[param_name] is None:
                return f"缺少必需参数: {param_name}"
        return None
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    def to_openai_tool(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式
        
        Returns:
            OpenAI 工具定义字典
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }
    
    def to_langchain_tool(self) -> Dict[str, Any]:
        """
        转换为 LangChain 工具格式
        
        Returns:
            LangChain 工具定义字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema
        }


class ToolRegistry:
    """
    工具注册表
    
    管理所有工具的注册、查找和执行
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __new__(cls) -> "ToolRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, BaseTool] = {}
            cls._instance._tools_by_category: Dict[ToolCategory, List[str]] = {
                category: [] for category in ToolCategory
            }
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")
        
        self._tools[tool.name] = tool
        self._tools_by_category[tool.category].append(tool.name)
        logger.info(f"已注册工具: {tool.name} (类别: {tool.category.value})")
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否成功注销
        """
        if tool_name not in self._tools:
            return False
        
        tool = self._tools[tool_name]
        del self._tools[tool_name]
        self._tools_by_category[tool.category].remove(tool_name)
        logger.info(f"已注销工具: {tool_name}")
        return True
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例，不存在返回 None
        """
        return self._tools.get(tool_name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        获取指定类别的所有工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具实例列表
        """
        return [
            self._tools[name] 
            for name in self._tools_by_category[category]
            if name in self._tools
        ]
    
    def list_tools(self) -> List[str]:
        """获取所有已注册工具名称"""
        return list(self._tools.keys())
    
    def list_tools_info(self) -> List[Dict[str, Any]]:
        """获取所有工具的信息摘要"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "required_parameters": tool.required_parameters
            }
            for tool in self._tools.values()
        ]
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI 格式定义"""
        return [tool.to_openai_tool() for tool in self._tools.values()]
    
    def get_langchain_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具的 LangChain 格式定义"""
        return [tool.to_langchain_tool() for tool in self._tools.values()]
    
    async def execute_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> ToolResult:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return ToolResult.fail(f"工具 '{tool_name}' 不存在")
        
        validation_error = tool.validate_parameters(params)
        if validation_error:
            return ToolResult.fail(validation_error)
        
        try:
            logger.info(f"执行工具: {tool_name}, 参数: {params}")
            result = await tool.execute(**params)
            logger.info(f"工具 {tool_name} 执行完成, 成功: {result.success}")
            return result
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行异常: {e}", exc_info=True)
            return ToolResult.fail(f"工具执行异常: {str(e)}")
    
    def clear(self) -> None:
        """清空所有注册的工具"""
        self._tools.clear()
        for category in self._tools_by_category:
            self._tools_by_category[category] = []
        logger.info("已清空所有工具注册")


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    工具注册装饰器
    
    使用方式:
        @register_tool
        class MyTool(BaseTool):
            ...
    """
    registry = ToolRegistry()
    tool_instance = tool_class()
    registry.register(tool_instance)
    return tool_class


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    return ToolRegistry()
