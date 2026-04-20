"""
RAGService 单元测试
测试 RAG（检索增强生成）服务的核心功能，包括检索、上下文构建、重排序等
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRAGService:
    """RAGService 测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的准备工作"""
        # 清除 lru_cache 缓存
        from app.services.rag_service import get_rag_service
        get_rag_service.cache_clear()

    def test_singleton_pattern(self):
        """测试单例模式：多次获取实例应返回同一对象"""
        from app.services.rag_service import get_rag_service
        
        service1 = get_rag_service()
        service2 = get_rag_service()
        
        assert service1 is service2, "工厂函数应返回同一实例"

    def test_context_type_prompts(self):
        """测试上下文类型提示映射"""
        from app.services.rag_service import RAGService
        
        expected_types = [
            "fundamental", "technical", "risk", 
            "sentiment", "decision", "general"
        ]
        
        for context_type in expected_types:
            assert context_type in RAGService.CONTEXT_TYPE_PROMPTS, \
                f"应包含上下文类型: {context_type}"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_retrieve_success(self, mock_get_vector_store):
        """测试检索功能"""
        from app.services.rag_service import RAGService
        
        # 模拟向量存储服务
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["相关文档1", "相关文档2"],
            "metadatas": [{"source": "test1"}, {"source": "test2"}],
            "distances": [0.1, 0.3],
            "ids": ["id1", "id2"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        results = service.retrieve(
            query="测试查询",
            collection_name="fund_knowledge",
            top_k=3
        )
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert "content" in results[0]
        assert "score" in results[0]
        assert "metadata" in results[0]
        assert "document_id" in results[0]

    @patch('app.services.rag_service.get_vector_store_service')
    def test_retrieve_empty_query(self, mock_get_vector_store):
        """测试空查询"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        # 空字符串
        results = service.retrieve(query="")
        assert results == [], "空查询应返回空列表"
        
        # 仅空白字符
        results = service.retrieve(query="   ")
        assert results == [], "仅空白字符应返回空列表"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_retrieve_with_filters(self, mock_get_vector_store):
        """测试带过滤条件的检索"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["过滤后的文档"],
            "metadatas": [{"source": "analysis_report"}],
            "distances": [0.2],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        results = service.retrieve(
            query="测试查询",
            filters={"source": "analysis_report"}
        )
        
        # 验证过滤条件被传递
        call_args = mock_vector_store.query.call_args
        assert call_args.kwargs.get("where") == {"source": "analysis_report"}

    @patch('app.services.rag_service.get_vector_store_service')
    def test_build_context_success(self, mock_get_vector_store):
        """测试上下文构建"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["这是第一段相关内容", "这是第二段相关内容"],
            "metadatas": [
                {"source": "分析报告", "type": "基本面"},
                {"source": "投资策略", "type": "技术面"}
            ],
            "distances": [0.1, 0.2],
            "ids": ["id1", "id2"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        context = service.build_context(
            query="测试查询",
            collection_name="fund_knowledge",
            context_type="general"
        )
        
        assert isinstance(context, str)
        assert "相关知识" in context, "上下文应包含类型提示"
        assert "来源" in context, "上下文应包含来源信息"
        assert "相关度" in context, "上下文应包含相关度信息"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_build_context_empty_results(self, mock_get_vector_store):
        """测试无检索结果时的上下文构建"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": [],
            "metadatas": [],
            "distances": [],
            "ids": []
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        context = service.build_context(query="测试查询")
        
        assert context == "", "无结果时应返回空字符串"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_build_context_different_types(self, mock_get_vector_store):
        """测试不同上下文类型的构建"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["基本面分析内容"],
            "metadatas": [{}],
            "distances": [0.1],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        
        # 测试基本面类型
        context = service.build_context(query="测试", context_type="fundamental")
        assert "基本面分析相关知识" in context
        
        # 测试技术面类型
        context = service.build_context(query="测试", context_type="technical")
        assert "技术面分析相关知识" in context
        
        # 测试风险评估类型
        context = service.build_context(query="测试", context_type="risk")
        assert "风险评估相关知识" in context

    @patch('app.services.rag_service.get_vector_store_service')
    def test_retrieve_and_rerank(self, mock_get_vector_store):
        """测试检索并重排序"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": [
                "包含测试关键词的文档",
                "普通文档内容",
                "另一个测试相关文档"
            ],
            "metadatas": [{}, {}, {}],
            "distances": [0.2, 0.1, 0.3],
            "ids": ["id1", "id2", "id3"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        results = service.retrieve_and_rerank(
            query="测试",
            top_k=10,
            final_k=2
        )
        
        assert len(results) <= 2, "应返回最多 final_k 个结果"
        assert all("reranked_score" in r for r in results), "结果应包含重排序分数"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_rerank_by_relevance(self, mock_get_vector_store):
        """测试相关性重排序"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        results = [
            {"content": "普通文档", "score": 0.8, "metadata": {}},
            {"content": "包含关键词测试的文档", "score": 0.7, "metadata": {}},
            {"content": "重要文档", "score": 0.6, "metadata": {"importance": 8}}
        ]
        
        reranked = service._rerank_by_relevance("测试", results)
        
        # 验证结果按分数降序排列
        scores = [r["reranked_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True), "结果应按分数降序排列"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_get_context_for_agent(self, mock_get_vector_store):
        """测试为特定智能体获取上下文"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["基本面分析相关内容"],
            "metadatas": [{}],
            "distances": [0.1],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        
        # 测试基本面智能体
        context = service.get_context_for_agent(
            agent_type="fundamental",
            query="测试查询"
        )
        assert "基本面分析相关知识" in context
        
        # 测试技术面智能体
        context = service.get_context_for_agent(
            agent_type="technical",
            query="测试查询"
        )
        assert "技术面分析相关知识" in context
        
        # 测试未知类型智能体（应使用通用类型）
        context = service.get_context_for_agent(
            agent_type="unknown_type",
            query="测试查询"
        )
        assert "基金投资相关知识" in context

    @patch('app.services.rag_service.get_vector_store_service')
    def test_batch_retrieve(self, mock_get_vector_store):
        """测试批量检索"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        
        def mock_query(**kwargs):
            query_text = kwargs.get("query_text", "")
            return {
                "documents": [f"结果: {query_text}"],
                "metadatas": [{}],
                "distances": [0.1],
                "ids": ["id1"]
            }
        
        mock_vector_store.query.side_effect = mock_query
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        
        queries = ["查询1", "查询2", "查询3"]
        results = service.batch_retrieve(queries)
        
        assert isinstance(results, dict)
        assert len(results) == 3
        for query in queries:
            assert query in results
            assert isinstance(results[query], list)

    @patch('app.services.rag_service.get_vector_store_service')
    def test_batch_retrieve_with_empty_query(self, mock_get_vector_store):
        """测试批量检索包含空查询"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        
        queries = ["有效查询", "", "   "]
        results = service.batch_retrieve(queries)
        
        assert results[""] == [], "空查询应返回空列表"
        assert results["   "] == [], "仅空白字符应返回空列表"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_score_calculation(self, mock_get_vector_store):
        """测试分数计算（距离转换为相似度）"""
        from app.services.rag_service import RAGService
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": ["文档"],
            "metadatas": [{}],
            "distances": [0.25],  # 距离 0.25 -> 相似度 0.75
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        results = service.retrieve(query="测试")
        
        assert len(results) == 1
        assert results[0]["score"] == 0.75, "相似度应为 1 - 距离"

    @patch('app.services.rag_service.get_vector_store_service')
    def test_content_truncation_in_context(self, mock_get_vector_store):
        """测试上下文中长内容的截断"""
        from app.services.rag_service import RAGService
        
        # 创建超长内容
        long_content = "这是一段很长的内容。" * 200  # 超过300字符
        
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = {
            "documents": [long_content],
            "metadatas": [{}],
            "distances": [0.1],
            "ids": ["id1"]
        }
        mock_get_vector_store.return_value = mock_vector_store
        
        service = RAGService()
        context = service.build_context(query="测试")
        
        # 验证内容被截断（包含省略号）
        assert "..." in context, "长内容应被截断并添加省略号"
