"""
Knowledge API 端点单元测试
测试知识库管理 API 的核心功能，包括文档上传、文本导入、搜索、删除等
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO


class TestKnowledgeAPI:
    """Knowledge API 测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = MagicMock()
        user.username = "test_user"
        user.id = 1
        user.is_active = True
        return user

    @pytest.fixture
    def auth_headers(self, mock_user):
        """模拟认证头"""
        # 返回空的认证头，因为我们会 mock 认证依赖
        return {}

    def test_search_knowledge_unauthorized(self, client):
        """测试未认证用户搜索知识接口"""
        response = client.get(
            "/api/v1/knowledge/search",
            params={"query": "测试查询", "top_k": 5}
        )
        
        # 未认证应返回 401
        assert response.status_code == 401

    def test_list_collections_unauthorized(self, client):
        """测试未认证用户获取集合列表接口"""
        response = client.get("/api/v1/knowledge/collections")
        
        # 未认证应返回 401
        assert response.status_code == 401

    def test_upload_document_unauthorized(self, client):
        """测试未认证用户上传文档接口"""
        # 创建模拟文件
        file_content = b"测试文件内容"
        file = BytesIO(file_content)
        
        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.txt", file, "text/plain")},
            data={
                "title": "测试文档",
                "doc_type": "analysis_report",
                "tags": "测试"
            }
        )
        
        # 未认证应返回 401
        assert response.status_code == 401

    def test_import_text_unauthorized(self, client):
        """测试未认证用户导入文本接口"""
        response = client.post(
            "/api/v1/knowledge/documents/text",
            json={
                "title": "测试文档",
                "content": "这是测试内容",
                "doc_type": "analysis_report",
                "tags": ["测试"]
            }
        )
        
        # 未认证应返回 401
        assert response.status_code == 401

    def test_delete_document_unauthorized(self, client):
        """测试未认证用户删除文档接口"""
        response = client.delete("/api/v1/knowledge/documents/test_doc_id")
        
        # 未认证应返回 401
        assert response.status_code == 401

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_search_knowledge_success(self, mock_get_service, mock_auth, client, mock_user):
        """测试认证用户搜索知识接口成功"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.search.return_value = [
            {
                "content": "相关文档内容",
                "score": 0.85,
                "metadata": {"source": "test"},
                "document_id": "doc_123"
            }
        ]
        mock_get_service.return_value = mock_service
        
        response = client.get(
            "/api/v1/knowledge/search",
            params={"query": "测试查询", "top_k": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "results" in data["data"]
        assert data["data"]["query"] == "测试查询"

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_vector_store_service')
    def test_list_collections_success(self, mock_get_store, mock_auth, client, mock_user):
        """测试认证用户获取集合列表成功"""
        mock_auth.return_value = mock_user
        
        mock_store = MagicMock()
        mock_store.list_collections.return_value = ["fund_knowledge", "analysis_cases"]
        mock_store.get_collection_count.return_value = 10
        mock_get_store.return_value = mock_store
        
        response = client.get("/api/v1/knowledge/collections")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "collections" in data["data"]

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_import_text_success(self, mock_get_service, mock_auth, client, mock_user):
        """测试认证用户导入文本成功"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.import_text.return_value = "doc_123"
        mock_service.get_document.return_value = {
            "id": "doc_123",
            "title": "测试文档",
            "content": "这是测试内容",
            "doc_type": MagicMock(value="analysis_report"),
            "tags": ["测试"],
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "chunk_count": 1
        }
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/knowledge/documents/text",
            json={
                "title": "测试文档",
                "content": "这是测试内容",
                "doc_type": "analysis_report",
                "tags": ["测试"],
                "metadata": {}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == "doc_123"

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_import_text_empty_content(self, mock_get_service, mock_auth, client, mock_user):
        """测试导入空内容"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.import_text.side_effect = ValueError("内容不能为空")
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/knowledge/documents/text",
            json={
                "title": "测试文档",
                "content": "",
                "doc_type": "analysis_report",
                "tags": []
            }
        )
        
        assert response.status_code == 400

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_delete_document_success(self, mock_get_service, mock_auth, client, mock_user):
        """测试认证用户删除文档成功"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.delete_document.return_value = True
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/knowledge/documents/doc_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_delete_document_not_found(self, mock_get_service, mock_auth, client, mock_user):
        """测试删除不存在的文档"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.delete_document.return_value = False
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/knowledge/documents/nonexistent_doc")
        
        assert response.status_code == 404

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_upload_document_invalid_type(self, mock_get_service, mock_auth, client, mock_user):
        """测试上传不支持的文件类型"""
        mock_auth.return_value = mock_user
        
        # 创建不支持类型的文件
        file_content = b"test content"
        file = BytesIO(file_content)
        
        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.xyz", file, "application/octet-stream")},
            data={
                "title": "测试文档",
                "doc_type": "analysis_report",
                "tags": ""
            }
        )
        
        assert response.status_code == 400
        assert "不支持的文件类型" in response.json()["detail"]

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_search_with_doc_type_filter(self, mock_get_service, mock_auth, client, mock_user):
        """测试带文档类型过滤的搜索"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_get_service.return_value = mock_service
        
        response = client.get(
            "/api/v1/knowledge/search",
            params={
                "query": "测试查询",
                "top_k": 5,
                "doc_type": "analysis_report"
            }
        )
        
        assert response.status_code == 200
        # 验证搜索方法被调用
        mock_service.search.assert_called_once()

    @patch('app.api.v1.endpoints.knowledge.get_current_active_user')
    @patch('app.api.v1.endpoints.knowledge.get_knowledge_service')
    def test_search_with_tags_filter(self, mock_get_service, mock_auth, client, mock_user):
        """测试带标签过滤的搜索"""
        mock_auth.return_value = mock_user
        
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_get_service.return_value = mock_service
        
        response = client.get(
            "/api/v1/knowledge/search",
            params={
                "query": "测试查询",
                "top_k": 5,
                "tags": "基金,投资"
            }
        )
        
        assert response.status_code == 200

    def test_search_missing_query(self, client):
        """测试搜索缺少查询参数"""
        response = client.get("/api/v1/knowledge/search")
        
        # 缺少必需参数应返回 422
        assert response.status_code == 422

    def test_search_invalid_top_k(self, client):
        """测试搜索无效的 top_k 参数"""
        response = client.get(
            "/api/v1/knowledge/search",
            params={"query": "测试", "top_k": 0}
        )
        
        # top_k 应 >= 1
        assert response.status_code == 422

    def test_search_top_k_too_large(self, client):
        """测试搜索 top_k 参数过大"""
        response = client.get(
            "/api/v1/knowledge/search",
            params={"query": "测试", "top_k": 100}
        )
        
        # top_k 应 <= 20
        assert response.status_code == 422
