"""
数据源适配器测试

测试 TushareAdapter 和 AkshareAdapter 的基本结构和核心方法
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

from app.data_sources.tushare_adapter import TushareAdapter
from app.data_sources.akshare_adapter import AkshareAdapter
from app.data_sources.base import BaseDataSource


class TestTushareAdapter:
    """TushareAdapter 测试类"""

    def test_tushare_adapter_inherits_base(self):
        """测试 TushareAdapter 继承自 BaseDataSource"""
        assert issubclass(TushareAdapter, BaseDataSource)

    @patch("app.data_sources.tushare_adapter.ts")
    @patch("app.data_sources.tushare_adapter.get_settings_manager")
    def test_tushare_adapter_init_without_token(self, mock_sm, mock_ts):
        """测试无 token 时初始化不可用"""
        mock_sm_instance = Mock()
        mock_sm_instance.get.return_value = None
        mock_sm.return_value = mock_sm_instance

        with patch("app.data_sources.tushare_adapter.settings") as mock_settings:
            mock_settings.TUSHARE_TOKEN = ""
            adapter = TushareAdapter()

        assert adapter.is_available is False
        assert adapter.name == "tushare"

    @patch("app.data_sources.tushare_adapter.ts")
    @patch("app.data_sources.tushare_adapter.get_settings_manager")
    def test_tushare_adapter_init_with_token(self, mock_sm, mock_ts):
        """测试有 token 时初始化创建客户端"""
        mock_sm_instance = Mock()
        mock_sm_instance.get.return_value = "test_token_123"
        mock_sm.return_value = mock_sm_instance

        mock_pro = Mock()
        mock_ts.set_token.return_value = None
        mock_ts.pro_api.return_value = mock_pro

        with patch("app.data_sources.tushare_adapter.settings") as mock_settings:
            mock_settings.TUSHARE_TOKEN = "test_token_123"
            adapter = TushareAdapter()

        assert adapter.is_available is True
        assert adapter._pro is not None

    @pytest.mark.asyncio
    async def test_call_pro_wraps_sync_call(self):
        """测试 _call_pro 将同步调用包装为异步执行"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"
        adapter.is_available = True
        adapter._token = "test_token"
        adapter._pro = None

        # 创建一个模拟的同步函数
        mock_func = Mock(return_value=pd.DataFrame({"col": [1, 2, 3]}))

        result = await adapter._call_pro(mock_func, arg1="value1", arg2="value2")

        # 验证同步函数被调用，且参数被正确传递
        mock_func.assert_called_once_with(arg1="value1", arg2="value2")
        # 验证返回值正确
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_call_pro_with_empty_result(self):
        """测试 _call_pro 返回空 DataFrame"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"
        adapter.is_available = True
        adapter._token = "test_token"
        adapter._pro = None

        mock_func = Mock(return_value=pd.DataFrame())

        result = await adapter._call_pro(mock_func)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_ensure_available_raises_when_unavailable(self):
        """测试数据源不可用时调用 _ensure_available 抛出异常"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"
        adapter.is_available = False
        adapter._pro = None
        adapter._token = ""

        with pytest.raises(RuntimeError, match="Tushare 数据源不可用"):
            adapter._ensure_available()

    def test_format_date(self):
        """测试日期格式化"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"

        from datetime import date
        result = adapter._format_date(date(2024, 3, 15))
        assert result == "20240315"

    def test_parse_date_valid(self):
        """测试有效日期字符串解析"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"

        from datetime import date
        result = adapter._parse_date("20240315")
        assert result == date(2024, 3, 15)

    def test_parse_date_empty(self):
        """测试空日期字符串返回None"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"

        result = adapter._parse_date("")
        assert result is None

    def test_parse_date_invalid(self):
        """测试无效日期字符串返回None"""
        adapter = TushareAdapter.__new__(TushareAdapter)
        adapter.name = "tushare"

        result = adapter._parse_date("not-a-date")
        assert result is None


class TestAkshareAdapter:
    """AkshareAdapter 测试类"""

    def test_akshare_adapter_inherits_base(self):
        """测试 AkshareAdapter 继承自 BaseDataSource"""
        assert issubclass(AkshareAdapter, BaseDataSource)

    def test_akshare_adapter_has_required_methods(self):
        """测试 AkshareAdapter 实现了所有必需的抽象方法"""
        required_methods = [
            "get_fund_info",
            "search_funds",
            "get_nav_history",
            "get_holdings",
            "check_health",
        ]
        for method_name in required_methods:
            assert hasattr(AkshareAdapter, method_name), f"缺少方法: {method_name}"

    def test_ensure_available_raises_when_unavailable(self):
        """测试数据源不可用时调用 _ensure_available 抛出异常"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"
        adapter.is_available = False

        with pytest.raises(RuntimeError, match="Akshare 数据源不可用"):
            adapter._ensure_available()

    def test_safe_float_with_normal_value(self):
        """测试正常浮点数转换"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        assert adapter._safe_float(3.14) == 3.14
        assert adapter._safe_float(42) == 42.0
        assert adapter._safe_float("2.5") == 2.5

    def test_safe_float_with_percent_string(self):
        """测试百分比字符串转换"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        assert adapter._safe_float("3.5%") == 3.5
        assert adapter._safe_float("0.15%") == 0.15

    def test_safe_float_with_none_and_nan(self):
        """测试 None 和 NaN 输入返回 None"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        assert adapter._safe_float(None) is None
        assert adapter._safe_float(float("nan")) is None

    def test_parse_date_multiple_formats(self):
        """测试多种日期格式解析"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        from datetime import date
        assert adapter._parse_date("2024-03-15") == date(2024, 3, 15)
        assert adapter._parse_date("20240315") == date(2024, 3, 15)
        assert adapter._parse_date("2024/03/15") == date(2024, 3, 15)

    def test_parse_date_empty_returns_none(self):
        """测试空字符串解析返回None"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        assert adapter._parse_date("") is None
        assert adapter._parse_date(None) is None

    def test_format_date_str(self):
        """测试日期格式化为字符串"""
        adapter = AkshareAdapter.__new__(AkshareAdapter)
        adapter.name = "akshare"

        from datetime import date
        result = adapter._format_date_str(date(2024, 3, 15))
        assert result == "2024-03-15"


class TestBaseDataSource:
    """BaseDataSource 基类测试"""

    def test_base_is_abstract(self):
        """测试 BaseDataSource 是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            BaseDataSource("test")

    def test_base_defines_required_methods(self):
        """测试基类定义了所有必需的抽象方法"""
        required_methods = [
            "get_fund_info",
            "search_funds",
            "get_nav_history",
            "get_holdings",
            "check_health",
        ]
        for method_name in required_methods:
            assert hasattr(BaseDataSource, method_name), f"基类缺少方法: {method_name}"
