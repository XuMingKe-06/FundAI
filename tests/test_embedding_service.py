"""
EmbeddingService 单元测试
测试文本向量化服务的核心功能，包括单例模式、向量化、缓存机制等
"""
import pytest
from unittest.mock import patch, MagicMock


class TestEmbeddingService:
    """EmbeddingService 测试类"""

    def test_singleton_pattern(self):
        """测试单例模式：多次获取实例应返回同一对象"""
        from app.services.embedding_service import EmbeddingService
        
        # 重置单例状态
        EmbeddingService._instance = None
        EmbeddingService._model = None
        EmbeddingService._dimension = None
        
        service1 = EmbeddingService()
        service2 = EmbeddingService()
        
        assert service1 is service2, "单例模式应返回同一实例"

    def test_get_embedding_service_singleton(self):
        """测试 get_embedding_service 工厂函数的单例行为"""
        from app.services.embedding_service import get_embedding_service
        
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2, "工厂函数应返回同一实例"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_embed_query_returns_list(self, mock_load_model):
        """测试 embed_query 返回浮点数列表"""
        from app.services.embedding_service import EmbeddingService
        
        # 重置单例状态
        EmbeddingService._instance = None
        EmbeddingService._model = None
        
        # 模拟模型
        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_model.encode.return_value = mock_embedding
        mock_model.get_sentence_embedding_dimension.return_value = 5
        
        service = EmbeddingService()
        service._model = mock_model
        service._dimension = 5
        
        result = service.embed_query("测试文本")
        
        assert isinstance(result, list), "结果应为列表类型"
        assert len(result) == 5, "向量维度应为5"
        assert all(isinstance(v, float) for v in result), "向量元素应为浮点数"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_embed_query_empty_text(self, mock_load_model):
        """测试 embed_query 对空文本的处理"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        service = EmbeddingService()
        
        # 空字符串
        result = service.embed_query("")
        assert result == [], "空字符串应返回空列表"
        
        # 仅包含空白字符
        result = service.embed_query("   ")
        assert result == [], "仅空白字符应返回空列表"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_embed_documents_batch(self, mock_load_model):
        """测试 embed_documents 批量向量化"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        
        # 模拟模型
        mock_model = MagicMock()
        mock_embeddings = [
            MagicMock(tostring=lambda: None) for _ in range(3)
        ]
        for i, emb in enumerate(mock_embeddings):
            emb.tolist.return_value = [float(i)] * 5
        
        mock_model.encode.return_value = mock_embeddings
        mock_model.get_sentence_embedding_dimension.return_value = 5
        
        service = EmbeddingService()
        service._model = mock_model
        service._dimension = 5
        
        texts = ["文本1", "文本2", "文本3"]
        results = service.embed_documents(texts)
        
        assert len(results) == len(texts), "结果数量应与输入数量一致"
        assert all(len(v) == 5 for v in results), "每个向量维度应一致"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_embed_documents_empty_list(self, mock_load_model):
        """测试 embed_documents 对空列表的处理"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        service = EmbeddingService()
        
        result = service.embed_documents([])
        assert result == [], "空列表应返回空列表"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_get_embedding_dimension(self, mock_load_model):
        """测试获取向量维度"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        
        service = EmbeddingService()
        service._model = mock_model
        service._dimension = 768
        
        dim = service.get_embedding_dimension()
        
        assert isinstance(dim, int), "维度应为整数"
        assert dim == 768, "维度应为768"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_cache_mechanism(self, mock_load_model):
        """测试缓存机制：相同文本应从缓存获取"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        
        # 模拟模型
        mock_model = MagicMock()
        call_count = [0]
        
        def mock_encode(text, **kwargs):
            call_count[0] += 1
            mock_embedding = MagicMock()
            mock_embedding.tolist.return_value = [0.1 * call_count[0]] * 5
            return mock_embedding
        
        mock_model.encode = mock_encode
        mock_model.get_sentence_embedding_dimension.return_value = 5
        
        service = EmbeddingService()
        service._model = mock_model
        service._dimension = 5
        service.clear_cache()
        
        text = "缓存测试文本"
        
        # 第一次调用
        v1 = service.embed_query(text)
        cache_size_1 = service.get_cache_size()
        
        # 第二次调用（应从缓存获取）
        v2 = service.embed_query(text)
        cache_size_2 = service.get_cache_size()
        
        assert v1 == v2, "缓存命中应返回相同结果"
        assert cache_size_1 == cache_size_2, "缓存大小应保持不变"
        assert call_count[0] == 1, "模型编码应只调用一次"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_clear_cache(self, mock_load_model):
        """测试清空缓存"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        
        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 5
        mock_model.encode.return_value = mock_embedding
        mock_model.get_sentence_embedding_dimension.return_value = 5
        
        service = EmbeddingService()
        service._model = mock_model
        service._dimension = 5
        
        # 添加缓存
        service.embed_query("测试文本1")
        service.embed_query("测试文本2")
        
        assert service.get_cache_size() == 2, "缓存应有2条记录"
        
        # 清空缓存
        service.clear_cache()
        
        assert service.get_cache_size() == 0, "清空后缓存应为空"

    @patch('app.services.embedding_service.EmbeddingService._load_model')
    def test_get_cache_size(self, mock_load_model):
        """测试获取缓存大小"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        service = EmbeddingService()
        service.clear_cache()
        
        assert service.get_cache_size() == 0, "初始缓存大小应为0"

    def test_get_cache_key_consistency(self):
        """测试缓存键生成的一致性"""
        from app.services.embedding_service import EmbeddingService
        
        EmbeddingService._instance = None
        service = EmbeddingService()
        
        text = "测试文本"
        key1 = service._get_cache_key(text)
        key2 = service._get_cache_key(text)
        
        assert key1 == key2, "相同文本应生成相同的缓存键"
        assert key1.startswith("emb:"), "缓存键应以 'emb:' 开头"
