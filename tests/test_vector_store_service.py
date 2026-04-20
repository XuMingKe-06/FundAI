"""
VectorStoreService 单元测试
测试向量存储服务的核心功能，包括单例模式、文档增删改查、集合管理等
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock, PropertyMock


class TestVectorStoreService:
    """VectorStoreService 测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的准备工作"""
        from app.services.vector_store_service import VectorStoreService
        
        # 重置单例状态
        VectorStoreService._instance = None
        VectorStoreService._client = None
        VectorStoreService._embedding_service = None
        
        self.test_collection = f"test_collection_{uuid.uuid4().hex[:8]}"

    def test_singleton_pattern(self):
        """测试单例模式：多次获取实例应返回同一对象"""
        from app.services.vector_store_service import VectorStoreService
        
        service1 = VectorStoreService()
        service2 = VectorStoreService()
        
        assert service1 is service2, "单例模式应返回同一实例"

    def test_get_vector_store_service_singleton(self):
        """测试 get_vector_store_service 工厂函数的单例行为"""
        from app.services.vector_store_service import get_vector_store_service
        
        service1 = get_vector_store_service()
        service2 = get_vector_store_service()
        
        assert service1 is service2, "工厂函数应返回同一实例"

    def test_collection_constants(self):
        """测试集合名称常量"""
        from app.services.vector_store_service import VectorStoreService
        
        assert VectorStoreService.FUND_KNOWLEDGE == "fund_knowledge"
        assert VectorStoreService.ANALYSIS_CASES == "analysis_cases"
        assert VectorStoreService.INVESTMENT_STRATEGY == "investment_strategy"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_add_documents_success(self, mock_init_client):
        """测试成功添加文档"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        # 模拟集合
        mock_collection = MagicMock()
        mock_collection.add.return_value = None
        
        # 模拟 _get_or_create_collection
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            docs = ["测试文档1", "测试文档2", "测试文档3"]
            ids = service.add_documents(
                collection_name=self.test_collection,
                documents=docs
            )
            
            assert len(ids) == len(docs), "返回的ID数量应与文档数量一致"
            assert all(isinstance(id, str) for id in ids), "ID应为字符串类型"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_add_documents_empty_list(self, mock_init_client):
        """测试添加空文档列表"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        ids = service.add_documents(
            collection_name=self.test_collection,
            documents=[]
        )
        
        assert ids == [], "空列表应返回空列表"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_add_documents_with_custom_ids(self, mock_init_client):
        """测试使用自定义ID添加文档"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            docs = ["测试文档"]
            custom_ids = ["custom_id_123"]
            
            ids = service.add_documents(
                collection_name=self.test_collection,
                documents=docs,
                ids=custom_ids
            )
            
            assert ids == custom_ids, "应返回自定义ID"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_query_success(self, mock_init_client):
        """测试查询文档"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        # 模拟查询结果
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["文档1", "文档2"]],
            "metadatas": [[{"source": "test"}, {"source": "test"}]],
            "distances": [[0.1, 0.2]],
            "ids": [["id1", "id2"]]
        }
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            results = service.query(
                collection_name=self.test_collection,
                query_text="测试查询",
                n_results=2
            )
            
            assert "documents" in results
            assert "metadatas" in results
            assert "distances" in results
            assert "ids" in results
            assert len(results["documents"]) == 2

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_query_empty_text(self, mock_init_client):
        """测试空查询文本"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        # 空字符串
        results = service.query(
            collection_name=self.test_collection,
            query_text=""
        )
        
        assert results["documents"] == []
        assert results["metadatas"] == []
        assert results["distances"] == []
        assert results["ids"] == []
        
        # 仅空白字符
        results = service.query(
            collection_name=self.test_collection,
            query_text="   "
        )
        
        assert results["documents"] == []

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_delete_documents_success(self, mock_init_client):
        """测试删除文档"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        mock_collection.delete.return_value = None
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            result = service.delete_documents(
                collection_name=self.test_collection,
                ids=["id1", "id2"]
            )
            
            assert result is True, "删除成功应返回True"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_delete_documents_empty_ids(self, mock_init_client):
        """测试删除空ID列表"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        result = service.delete_documents(
            collection_name=self.test_collection,
            ids=[]
        )
        
        assert result is False, "空ID列表应返回False"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_delete_collection_success(self, mock_init_client):
        """测试删除集合"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        # 模拟客户端
        mock_client = MagicMock()
        mock_client.delete_collection.return_value = None
        service._client = mock_client
        service._collections = {self.test_collection: MagicMock()}
        
        result = service.delete_collection(self.test_collection)
        
        assert result is True, "删除成功应返回True"
        assert self.test_collection not in service._collections

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_list_collections(self, mock_init_client):
        """测试列出集合"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        # 模拟客户端
        mock_client = MagicMock()
        mock_collection1 = MagicMock()
        mock_collection1.name = "collection1"
        mock_collection2 = MagicMock()
        mock_collection2.name = "collection2"
        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]
        service._client = mock_client
        
        collections = service.list_collections()
        
        assert isinstance(collections, list)
        assert "collection1" in collections
        assert "collection2" in collections

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_get_collection_count(self, mock_init_client):
        """测试获取集合文档数量"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            count = service.get_collection_count(self.test_collection)
            
            assert count == 42

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_update_document_success(self, mock_init_client):
        """测试更新文档"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        mock_collection.update.return_value = None
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            result = service.update_document(
                collection_name=self.test_collection,
                document_id="doc_123",
                document="更新后的文档内容",
                metadata={"updated": True}
            )
            
            assert result is True, "更新成功应返回True"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_get_document_by_id_found(self, mock_init_client):
        """测试根据ID获取文档（存在）"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["doc_123"],
            "documents": ["文档内容"],
            "metadatas": [{"source": "test"}]
        }
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            result = service.get_document_by_id(
                collection_name=self.test_collection,
                document_id="doc_123"
            )
            
            assert result is not None
            assert result["id"] == "doc_123"
            assert result["document"] == "文档内容"
            assert result["metadata"]["source"] == "test"

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_get_document_by_id_not_found(self, mock_init_client):
        """测试根据ID获取文档（不存在）"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        
        with patch.object(service, '_get_or_create_collection', return_value=mock_collection):
            result = service.get_document_by_id(
                collection_name=self.test_collection,
                document_id="nonexistent_id"
            )
            
            assert result is None

    @patch('app.services.vector_store_service.VectorStoreService._initialize_client')
    def test_reset_database(self, mock_init_client):
        """测试重置数据库"""
        from app.services.vector_store_service import VectorStoreService
        
        VectorStoreService._instance = None
        service = VectorStoreService()
        
        mock_client = MagicMock()
        mock_client.reset.return_value = None
        service._client = mock_client
        service._collections = {"col1": MagicMock(), "col2": MagicMock()}
        
        result = service.reset_database()
        
        assert result is True, "重置成功应返回True"
        assert len(service._collections) == 0, "集合缓存应被清空"
