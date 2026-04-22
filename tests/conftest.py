"""
pytest配置和公共fixtures

提供测试所需的模拟数据和模拟服务
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_fund_info() -> Dict[str, Any]:
    """示例基金基础信息"""
    return {
        "fund_code": "000001",
        "fund_name": "华夏成长混合",
        "fund_type": "混合型",
        "fund_manager": "张三",
        "establish_date": "2001-12-18",
        "current_scale": 50.5,
        "management_fee": 1.5,
        "custodian_fee": 0.25
    }


@pytest.fixture
def sample_nav_history() -> List[Dict[str, Any]]:
    """示例净值历史数据"""
    base_nav = 1.5
    history = []
    for i in range(100):
        history.append({
            "date": (date.today() - timedelta(days=100-i)).strftime("%Y-%m-%d"),
            "nav": round(base_nav * (1 + 0.001 * i + 0.0005 * ((-1) ** i)), 4),
            "unit_nav": round(base_nav * (1 + 0.001 * i + 0.0005 * ((-1) ** i)), 4)
        })
    return history


@pytest.fixture
def sample_holdings() -> Dict[str, Any]:
    """示例持仓数据"""
    return {
        "report_date": "2024-06-30",
        "stock_list": [
            {"stock_code": "600519", "stock_name": "贵州茅台", "holding_ratio": 8.5, "industry": "食品饮料"},
            {"stock_code": "000858", "stock_name": "五粮液", "holding_ratio": 6.2, "industry": "食品饮料"},
            {"stock_code": "601318", "stock_name": "中国平安", "holding_ratio": 5.8, "industry": "保险"},
            {"stock_code": "000333", "stock_name": "美的集团", "holding_ratio": 4.5, "industry": "家用电器"},
            {"stock_code": "600036", "stock_name": "招商银行", "holding_ratio": 4.2, "industry": "银行"},
        ],
        "industry_list": [
            {"industry": "食品饮料", "proportion": 25.5},
            {"industry": "金融", "proportion": 18.3},
            {"industry": "家用电器", "proportion": 12.1},
        ]
    }


@pytest.fixture
def sample_fund_manager() -> Dict[str, Any]:
    """示例基金经理信息"""
    return {
        "manager_name": "张三",
        "experience_years": 8,
        "start_date": "2016-03-15",
        "annual_return": 12.5,
        "management_scale": 150.0,
        "managed_funds": 5
    }


@pytest.fixture
def sample_fees() -> Dict[str, Any]:
    """示例费率信息"""
    return {
        "purchase_fee_rate": 0.015,
        "redemption_fee_ladder": [
            {"holding_days": 7, "fee_rate": 0.015},
            {"holding_days": 30, "fee_rate": 0.0075},
            {"holding_days": 365, "fee_rate": 0.005},
            {"holding_days": 730, "fee_rate": 0.0}
        ],
        "management_fee_rate": 0.015,
        "custodian_fee_rate": 0.0025
    }


@pytest.fixture
def sample_llm_response() -> str:
    """示例LLM响应"""
    return json.dumps({
        "score": 3.5,
        "summary": "该基金基本面表现良好，基金经理经验丰富，持仓结构合理。",
        "details": {
            "fund_manager_score": 4.0,
            "holdings_score": 3.5,
            "performance_score": 3.0,
            "key_findings": [
                "基金经理从业8年，历史业绩优秀",
                "前十大持仓占比适中，行业分布均衡",
                "近1年超额收益5.2%"
            ]
        }
    }, ensure_ascii=False)


@pytest.fixture
def mock_llm_service(sample_llm_response):
    """模拟LLM服务"""
    mock_service = Mock()
    mock_service.chat_async = AsyncMock(return_value=sample_llm_response)
    mock_service.get_model_name = Mock(return_value="test-model")
    mock_service.get_async_client = Mock()
    return mock_service


@pytest.fixture
def mock_datasource_manager(sample_fund_info, sample_nav_history, sample_holdings, sample_fund_manager, sample_fees):
    """模拟数据源管理器"""
    mock_manager = Mock()
    mock_manager.current_source_name = "test_source"
    mock_manager.get_fund_info = AsyncMock(return_value=sample_fund_info)
    mock_manager.get_nav_history = AsyncMock(return_value=sample_nav_history)
    mock_manager.get_holdings = AsyncMock(return_value=sample_holdings)
    mock_manager.get_fund_manager = AsyncMock(return_value=sample_fund_manager)
    mock_manager.get_fund_fees = AsyncMock(return_value=sample_fees)
    mock_manager.get_news_sentiment = AsyncMock(return_value=None)
    mock_manager.get_fund_flow = AsyncMock(return_value=None)
    mock_manager.get_social_heat = AsyncMock(return_value=None)
    mock_manager.get_institutional_views = AsyncMock(return_value=None)
    return mock_manager


@pytest.fixture
def mock_rag_service():
    """模拟RAG服务"""
    mock_service = Mock()
    mock_service.retrieve = Mock(return_value=[
        {"content": "测试知识内容1", "score": 0.9},
        {"content": "测试知识内容2", "score": 0.8}
    ])
    mock_service.build_context = Mock(return_value="【相关知识】\n1. 测试知识内容1\n2. 测试知识内容2")
    return mock_service


@pytest.fixture
def sample_analysis_context(sample_fund_info, sample_nav_history):
    """示例分析上下文"""
    return {
        "fund_code": "000001",
        "fund_info": sample_fund_info,
        "nav_history": sample_nav_history,
        "user_preference": "neutral",
        "session_id": "test-session-001"
    }


@pytest.fixture
def sample_agent_results():
    """示例智能体分析结果"""
    return {
        "fundamental": {
            "score": 3.5,
            "summary": "基本面表现良好",
            "details": {"fund_manager_score": 4.0}
        },
        "technical": {
            "score": 3.8,
            "summary": "技术面向好",
            "details": {"ma_trend": "多头排列"}
        },
        "risk": {
            "score": 4.0,
            "summary": "风险水平适中",
            "details": {"risk_level": "中"}
        },
        "cost": {
            "score": 3.2,
            "summary": "成本适中",
            "details": {"short_term_feasibility": "可行"}
        },
        "sentiment": {
            "score": 1.5,
            "summary": "市场情绪偏正面",
            "details": {"sentiment_score": 1.5}
        }
    }
