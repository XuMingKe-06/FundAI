"""
KnowledgeService 单元测试
测试知识库服务的核心功能，包括文档导入、文本分块、搜索等
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open


class TestKnowledgeService:
    """KnowledgeService 测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的准备工作"""
        pass

    def test_get_knowledge_service_returns_instance(self):
        """测试获取知识库服务实例"""
        from app.services.knowledge_service import get_knowledge_service, KnowledgeService
        
        service = get_knowledge_service()
        
        assert isinstance(service, KnowledgeService)

    def test_knowledge_collection_constant(self):
        """测试知识库集合名称常量"""
        from app.services.knowledge_service import KnowledgeService
        
        assert KnowledgeService.KNOWLEDGE_COLLECTION == "fund_knowledge"

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_import_text_success(self, mock_get_vector_store):
        """测试导入文本成功"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        mock_vector_store = MagicMock()
        mock_vector_store.add_documents.return_value = ["chunk_id_1", "chunk_id_2"]
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        doc_id = service.import_text(
            content="这是一段测试文本内容，用于测试导入功能。",
            title="测试文档",
            doc_type=KnowledgeDocumentType.ANALYSIS_REPORT,
            tags=["测试", "单元测试"]
        )
        
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0, "应返回有效的文档ID"
        mock_vector_store.add_documents.assert_called_once()

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_import_text_empty_content(self, mock_get_vector_store):
        """测试导入空文本"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        service = KnowledgeService()
        
        with pytest.raises(ValueError, match="内容不能为空"):
            service.import_text(
                content="",
                title="测试文档",
                doc_type=KnowledgeDocumentType.ANALYSIS_REPORT
            )

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_import_text_whitespace_only(self, mock_get_vector_store):
        """测试导入仅包含空白字符的文本"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        service = KnowledgeService()
        
        with pytest.raises(ValueError, match="内容不能为空"):
            service.import_text(
                content="   \n\t   ",
                title="测试文档",
                doc_type=KnowledgeDocumentType.ANALYSIS_REPORT
            )

    def test_split_text_success(self):
        """测试文本分块"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        # 创建一段测试文本
        text = "这是第一段内容。" * 50 + "这是第二段内容。" * 50
        
        chunks = service._split_text(text, chunk_size=100, chunk_overlap=20)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0, "应生成至少一个分块"
        assert all(isinstance(chunk, str) for chunk in chunks), "每个分块应为字符串"

    def test_split_text_empty(self):
        """测试空文本分块"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        chunks = service._split_text("")
        assert chunks == [], "空文本应返回空列表"
        
        chunks = service._split_text("   ")
        assert chunks == [], "仅空白字符应返回空列表"

    def test_split_text_short(self):
        """测试短文本分块"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        text = "这是一段短文本"
        chunks = service._split_text(text, chunk_size=100, chunk_overlap=20)
        
        assert len(chunks) == 1, "短文本应只生成一个分块"
        assert chunks[0] == text

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_search_success(self, mock_get_vector_store):
        """测试搜索功能"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["相关文档1", "相关文档2"],
            "metadatas": [
                {"document_id": "doc1", "doc_type": "analysis_report"},
                {"document_id": "doc2", "doc_type": "research_report"}
            ],
            "distances": [0.1, 0.3],
            "ids": ["id1", "id2"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        results = service.search(
            query="测试查询",
            top_k=5
        )
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert all("content" in r for r in results)
        assert all("score" in r for r in results)
        assert all("metadata" in r for r in results)
        assert all("document_id" in r for r in results)

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_search_with_doc_type_filter(self, mock_get_vector_store):
        """测试带文档类型过滤的搜索"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["分析报告内容"],
            "metadatas": [{"document_id": "doc1", "doc_type": "analysis_report"}],
            "distances": [0.1],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        results = service.search(
            query="测试查询",
            doc_type=KnowledgeDocumentType.ANALYSIS_REPORT,
            top_k=5
        )
        
        # 验证过滤条件被传递
        call_args = mock_vector_store.query.call_args
        assert call_args.kwargs.get("where") == {"doc_type": "analysis_report"}

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_search_with_tags_filter(self, mock_get_vector_store):
        """测试带标签过滤的搜索"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["带标签的文档"],
            "metadatas": [{"document_id": "doc1", "tags": "基金,投资"}],
            "distances": [0.1],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        results = service.search(
            query="测试查询",
            tags=["基金"],
            top_k=5
        )
        
        assert len(results) == 1

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_delete_document_success(self, mock_get_vector_store):
        """测试删除文档成功"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "ids": ["chunk1", "chunk2"],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        mock_vector_store.delete_documents.return_value = True
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        result = service.delete_document("doc_123")
        
        assert result is True

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_delete_document_not_found(self, mock_get_vector_store):
        """测试删除不存在的文档"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        result = service.delete_document("nonexistent_doc")
        
        assert result is False

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_get_document_success(self, mock_get_vector_store):
        """测试获取文档详情"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "ids": ["chunk1", "chunk2"],
            "documents": ["第一段内容", "第二段内容"],
            "metadatas": [
                {
                    "document_id": "doc_123",
                    "title": "测试文档",
                    "doc_type": "analysis_report",
                    "tags": "测试,基金",
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                },
                {
                    "document_id": "doc_123",
                    "title": "测试文档",
                    "doc_type": "analysis_report",
                    "tags": "测试,基金",
                    "chunk_index": 1,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            ],
            "distances": []
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        doc = service.get_document("doc_123")
        
        assert doc is not None
        assert doc["id"] == "doc_123"
        assert doc["title"] == "测试文档"
        assert doc["chunk_count"] == 2
        assert "第一段内容" in doc["content"]
        assert "第二段内容" in doc["content"]

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_get_document_not_found(self, mock_get_vector_store):
        """测试获取不存在的文档"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        doc = service.get_document("nonexistent_doc")
        
        assert doc is None

    def test_parse_text_file(self):
        """测试解析 TXT 文件"""
        from app.services.knowledge_service import KnowledgeService
        
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是测试文件内容\n第二行内容")
            temp_path = f.name
        
        try:
            service = KnowledgeService()
            content = service._parse_text_file(temp_path)
            
            assert content == "这是测试文件内容\n第二行内容"
        finally:
            os.unlink(temp_path)

    def test_parse_text_file_not_found(self):
        """测试解析不存在的 TXT 文件"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        with pytest.raises(FileNotFoundError):
            service._parse_text_file("/nonexistent/path/file.txt")

    def test_parse_markdown_file(self):
        """测试解析 Markdown 文件"""
        from app.services.knowledge_service import KnowledgeService
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# 标题\n\n这是正文内容")
            temp_path = f.name
        
        try:
            service = KnowledgeService()
            content = service._parse_markdown_file(temp_path)
            
            assert "# 标题" in content
            assert "这是正文内容" in content
        finally:
            os.unlink(temp_path)

    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        assert service._get_file_extension("test.txt") == ".txt"
        assert service._get_file_extension("test.PDF") == ".pdf"
        assert service._get_file_extension("path/to/test.MD") == ".md"

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_import_document_txt_file(self, mock_get_vector_store):
        """测试导入 TXT 文档"""
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import KnowledgeDocumentType
        
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是测试文档内容")
            temp_path = f.name
        
        try:
            mock_vector_store = MagicMock()
            mock_vector_store.add_documents.return_value = ["chunk_id"]
            mock_get_vector_store.return_value = mock_vector_store
            
            service = KnowledgeService()
            doc_id = service.import_document(
                file_path=temp_path,
                title="测试TXT文档",
                doc_type=KnowledgeDocumentType.RESEARCH_REPORT,
                tags=["测试"]
            )
            
            assert isinstance(doc_id, str)
            assert len(doc_id) > 0
        finally:
            os.unlink(temp_path)

    def test_parse_file_unsupported_type(self):
        """测试解析不支持的文件类型"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        
        with pytest.raises(ValueError, match="不支持的文件类型"):
            service._parse_file("test.xyz")

    @patch('app.services.knowledge_service.get_vector_store_service')
    def test_score_calculation_in_search(self, mock_get_vector_store):
        """测试搜索结果中的分数计算"""
        from app.services.knowledge_service import KnowledgeService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["文档内容"],
            "metadatas": [{"document_id": "doc1"}],
            "distances": [0.2],  # 距离 0.2 -> 相似度 0.8
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = KnowledgeService()
        results = service.search(query="测试")
        
        assert len(results) == 1
        assert results[0]["score"] == 0.8, "相似度应为 1 - 距离"
