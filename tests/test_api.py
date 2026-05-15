"""
API集成测试

测试 FastAPI 应用的基本端点：健康检查、根路径、404处理
"""
import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, client: AsyncClient):
        """测试健康检查端点返回200状态码"""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_response_format(self, client: AsyncClient):
        """测试健康检查端点返回正确的响应格式"""
        response = await client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_contains_app_name(self, client: AsyncClient):
        """测试健康检查响应包含应用名称"""
        response = await client.get("/health")
        data = response.json()

        assert data["app"] == "FundAI"


class TestRootEndpoint:
    """根路径端点测试"""

    @pytest.mark.asyncio
    async def test_root_returns_200(self, client: AsyncClient):
        """测试根路径返回200状态码"""
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_response_format(self, client: AsyncClient):
        """测试根路径返回正确的响应格式"""
        response = await client.get("/")
        data = response.json()

        assert "message" in data
        assert "docs" in data
        assert "health" in data

    @pytest.mark.asyncio
    async def test_root_contains_docs_link(self, client: AsyncClient):
        """测试根路径响应包含文档链接"""
        response = await client.get("/")
        data = response.json()

        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestNotFoundHandling:
    """404处理测试"""

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint_returns_404(self, client: AsyncClient):
        """测试访问不存在的端点返回404"""
        response = await client.get("/nonexistent-path")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_api_endpoint_returns_404(self, client: AsyncClient):
        """测试访问不存在的API端点返回404"""
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_has_error_format(self, client: AsyncClient):
        """测试404响应包含错误信息格式"""
        response = await client.get("/nonexistent-path")
        data = response.json()

        # FastAPI 默认404响应格式
        assert "detail" in data or "message" in data
