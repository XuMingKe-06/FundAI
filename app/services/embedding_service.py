"""
Embedding 服务模块
提供文本向量化功能，支持中文文本
支持三种模式：本地模型模式、OpenAI API 模式、阿里云 API 模式
"""
from typing import List, Optional
from functools import lru_cache
from app.core.config import settings


class EmbeddingService:
    """
    Embedding 服务类
    支持三种模式：
    - local: 使用 sentence-transformers 本地模型
    - api: 使用 OpenAI API
    - aliyun: 使用阿里云大模型 API
    """
    
    _instance: Optional["EmbeddingService"] = None
    _model: Optional[object] = None
    _dimension: Optional[int] = None
    
    def __new__(cls) -> "EmbeddingService":
        """
        单例模式，确保全局只有一个模型实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化 Embedding 服务
        模型延迟加载，不在初始化时加载
        """
        self._model_name = settings.EMBEDDING_MODEL_NAME
        self._mode = settings.EMBEDDING_MODE
        self._cache: dict = {}
    
    def _load_model(self):
        """
        延迟加载 embedding 模型
        只在第一次使用时加载模型
        """
        if self._model is not None:
            return
            
        if self._mode == "aliyun":
            self._load_aliyun_model()
        elif self._mode == "api":
            self._load_api_model()
        else:
            self._load_local_model()
    
    def _load_local_model(self):
        """
        加载本地 sentence-transformers 模型
        """
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
    
    def _load_api_model(self):
        """
        加载 OpenAI API 模型
        使用 OpenAI SDK
        """
        from openai import OpenAI
        
        self._model = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY or "sk-dummy-key",
            base_url=settings.DEEPSEEK_API_BASE
        )
        self._dimension = 1536
    
    def _load_aliyun_model(self):
        """
        加载阿里云大模型 embedding
        使用 OpenAI 兼容接口
        """
        from openai import OpenAI
        
        api_key = settings.ALIYUN_LLM_API_KEY
        if not api_key:
            raise ValueError("请配置 ALIYUN_LLM_API_KEY")
        
        self._model = OpenAI(
            api_key=api_key,
            base_url=settings.ALIYUN_LLM_API_BASE
        )
        self._dimension = 1024
    
    def _get_cache_key(self, text: str) -> str:
        """
        生成缓存键
        
        Args:
            text: 输入文本
            
        Returns:
            缓存键字符串
        """
        return f"emb:{hash(text)}"
    
    def embed_query(self, text: str) -> List[float]:
        """
        单个文本向量化
        
        Args:
            text: 待向量化的文本
            
        Returns:
            文本的向量表示（浮点数列表）
        """
        if not text or not text.strip():
            return []
        
        self._load_model()
        
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self._mode in ["api", "aliyun"]:
            response = self._model.embeddings.create(
                model=self._model_name if self._mode == "aliyun" else "text-embedding-ada-002",
                input=text
            )
            result = response.data[0].embedding
        else:
            embedding = self._model.encode(text, normalize_embeddings=True)
            result = embedding.tolist()
        
        self._cache[cache_key] = result
        return result
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化
        
        Args:
            texts: 待向量化的文本列表
            
        Returns:
            文本向量列表，每个元素是一个文本的向量表示
        """
        if not texts:
            return []
        
        self._load_model()
        
        results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append([])
                continue
                
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        if uncached_texts:
            if self._mode in ["api", "aliyun"]:
                response = self._model.embeddings.create(
                    model=self._model_name if self._mode == "aliyun" else "text-embedding-ada-002",
                    input=uncached_texts
                )
                embeddings = [item.embedding for item in response.data]
            else:
                embeddings = self._model.encode(
                    uncached_texts, 
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                embeddings = [e.tolist() for e in embeddings]
            
            for idx, text, embedding in zip(uncached_indices, uncached_texts, embeddings):
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = embedding
                results[idx] = embedding
        
        return results
    
    def get_embedding_dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            向量维度（整数）
        """
        self._load_model()
        return self._dimension
    
    def clear_cache(self):
        """
        清空缓存
        """
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存中的条目数量
        """
        return len(self._cache)


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """
    获取 Embedding 服务单例
    
    Returns:
        EmbeddingService 实例
    """
    return EmbeddingService()
