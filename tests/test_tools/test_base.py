"""
工具基类测试
"""
import pytest
from app.agents.tools.base import (
    ToolResult,
    ToolCategory,
    ToolRegistry,
    BaseTool,
    register_tool,
    get_tool_registry
)


class TestToolResult:
    """ToolResult测试类"""
    
    def test_tool_result_ok(self):
        """测试创建成功结果"""
        result = ToolResult.ok(data={"test": "data"})
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
    
    def test_tool_result_ok_with_metadata(self):
        """测试带元数据的成功结果"""
        result = ToolResult.ok(
            data={"test": "data"},
            metadata={"source": "test"}
        )
        
        assert result.success is True
        assert result.metadata == {"source": "test"}
    
    def test_tool_result_fail(self):
        """测试创建失败结果"""
        result = ToolResult.fail(error="测试错误")
        
        assert result.success is False
        assert result.error == "测试错误"
        assert result.data is None
    
    def test_tool_result_to_dict(self):
        """测试结果转换为字典"""
        result = ToolResult.ok(
            data={"test": "data"},
            metadata={"source": "test"}
        )
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "data" in result_dict
        assert "error" in result_dict
        assert "metadata" in result_dict


class MockTool(BaseTool):
    """模拟工具类"""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "模拟工具用于测试"
    
    @property
    def parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"},
                "param2": {"type": "integer", "description": "参数2"}
            },
            "required": ["param1"]
        }
    
    async def execute(self, **kwargs):
        return ToolResult.ok(data=kwargs)


class TestBaseTool:
    """BaseTool测试类"""
    
    def test_base_tool_properties(self):
        """测试工具基类属性"""
        tool = MockTool()
        
        assert tool.name == "mock_tool"
        assert tool.description == "模拟工具用于测试"
        assert "param1" in tool.parameters_schema["properties"]
    
    def test_base_tool_required_parameters(self):
        """测试必需参数列表"""
        tool = MockTool()
        
        assert "param1" in tool.required_parameters
    
    def test_base_tool_validate_parameters_success(self):
        """测试参数验证成功"""
        tool = MockTool()
        
        error = tool.validate_parameters({"param1": "test"})
        assert error is None
    
    def test_base_tool_validate_parameters_missing(self):
        """测试参数验证失败（缺少必需参数）"""
        tool = MockTool()
        
        error = tool.validate_parameters({"param2": 123})
        assert error is not None
        assert "param1" in error
    
    def test_base_tool_to_openai_tool(self):
        """测试转换为OpenAI工具格式"""
        tool = MockTool()
        openai_tool = tool.to_openai_tool()
        
        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "mock_tool"
        assert "parameters" in openai_tool["function"]


class TestToolRegistry:
    """ToolRegistry测试类"""
    
    def test_tool_registry_singleton(self):
        """测试注册表单例"""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()
        
        assert registry1 is registry2
    
    def test_tool_registry_register(self):
        """测试工具注册"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool()
        registry.register(tool)
        
        assert "mock_tool" in registry.list_tools()
    
    def test_tool_registry_get_tool(self):
        """测试获取工具"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool()
        registry.register(tool)
        
        retrieved = registry.get_tool("mock_tool")
        assert retrieved is not None
        assert retrieved.name == "mock_tool"
    
    def test_tool_registry_get_tool_not_found(self):
        """测试获取不存在的工具"""
        registry = ToolRegistry()
        
        retrieved = registry.get_tool("non_existent_tool")
        assert retrieved is None
    
    def test_tool_registry_list_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool()
        registry.register(tool)
        
        tools = registry.list_tools()
        assert "mock_tool" in tools
    
    def test_tool_registry_list_tools_info(self):
        """测试获取工具信息摘要"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool()
        registry.register(tool)
        
        info_list = registry.list_tools_info()
        assert len(info_list) > 0
        
        info = next((i for i in info_list if i["name"] == "mock_tool"), None)
        assert info is not None
        assert "description" in info
        assert "category" in info
    
    @pytest.mark.asyncio
    async def test_tool_registry_execute_tool(self):
        """测试执行工具"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool()
        registry.register(tool)
        
        result = await registry.execute_tool("mock_tool", {"param1": "test"})
        
        assert result.success is True
        assert result.data == {"param1": "test"}
    
    @pytest.mark.asyncio
    async def test_tool_registry_execute_tool_not_found(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()
        
        result = await registry.execute_tool("non_existent", {})
        
        assert result.success is False
        assert "不存在" in result.error
    
    def test_tool_registry_clear(self):
        """测试清空注册表"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        
        registry.clear()
        
        assert len(registry.list_tools()) == 0


def test_get_tool_registry():
    """测试获取工具注册表"""
    registry = get_tool_registry()
    assert isinstance(registry, ToolRegistry)
