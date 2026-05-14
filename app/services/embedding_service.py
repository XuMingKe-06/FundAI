"""
Embedding 服务模块
提供文本向量化功能，支持中文文本
支持两种模式：本地模型模式、远程 API 模式
配置从前端设置页面管理
"""
from typing import List, Optional
from functools import lru_cache
import re


# 不支持的模型模式（rerank 模型等）
UNSUPPORTED_MODEL_PATTERNS = [
    r'rerank',  # 重排序模型
    r'rank',    # 排序模型
]

# 推荐的 Embedding 模型列表
RECOMMENDED_EMBEDDING_MODELS = [
    'text-embedding-v4',
    'text-embedding-v3',
    'text-embedding-v2',
    'text-embedding-v1',
]


def is_valid_embedding_model(model_name: str) -> tuple[bool, str]:
    """
    验证模型名称是否为有效的 Embedding 模型
    
    Args:
        model_name: 模型名称
        
    Returns:
        (是否有效, 错误信息)
    """
    if not model_name:
        return False, "请在设置页面配置 Embedding 模型名称"
    
    model_lower = model_name.lower()
    
    for pattern in UNSUPPORTED_MODEL_PATTERNS:
        if re.search(pattern, model_lower):
            return False, (
                f"模型 '{model_name}' 是重排序模型，不支持文本向量化。"
                f"请使用 Embedding 模型，推荐: {', '.join(RECOMMENDED_EMBEDDING_MODELS)}"
            )
    
    return True, ""


class EmbeddingService:
    """
    Embedding 服务类
    支持两种模式：
    - local: 使用 sentence-transformers 本地模型
    - api: 使用远程 API（OpenAI 兼容接口）
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
        self._model_name: Optional[str] = None
        self._api_key: Optional[str] = None
        self._api_base_url: Optional[str] = None
        self._mode: Optional[str] = None
        self._cache: dict = {}
        self._initialized = False
    
    def _get_settings_manager(self):
        """获取配置管理器（延迟导入避免循环依赖）"""
        from app.core.settings_manager import get_settings_manager
        return get_settings_manager()
    
    def _load_config(self):
        """从配置管理器加载配置"""
        sm = self._get_settings_manager()
        self._api_base_url = sm.get("llm.embedding_api_base_url", "")
        self._api_key = sm.get("llm.embedding_api_key", "")
        self._model_name = sm.get("llm.embedding_model", "")
        self._mode = sm.get("rag.embedding_mode", "api")
    
    def _load_model(self):
        """
        延迟加载 embedding 模型
        只在第一次使用时加载模型
        """
        if self._model is not None:
            return
        
        self._load_config()
            
        if self._mode == "api":
            self._load_api_model()
        else:
            self._load_local_model()
    
    def _load_local_model(self):
        """
        加载本地 sentence-transformers 模型
        """
        if not self._model_name:
            raise ValueError("请在设置页面配置 Embedding 模型名称")
        
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
    
    def _load_api_model(self):
        """
        加载远程 API 模型
        使用 OpenAI SDK，支持 OpenAI 兼容接口
        """
        if not self._api_key:
            raise ValueError("请在设置页面配置 Embedding API Key")
        
        if not self._api_base_url:
            raise ValueError("请在设置页面配置 Embedding API Base URL")
        
        if not self._model_name:
            raise ValueError("请在设置页面配置 Embedding 模型名称")
        
        # 验证模型是否为有效的 Embedding 模型
        is_valid, error_msg = is_valid_embedding_model(self._model_name)
        if not is_valid:
            raise ValueError(error_msg)
        
        from openai import OpenAI
        
        self._model = OpenAI(
            api_key=self._api_key,
            base_url=self._api_base_url
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
        
        if self._mode == "api":
            response = self._model.embeddings.create(
                model=self._model_name,
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
            if self._mode == "api":
                response = self._model.embeddings.create(
                    model=self._model_name,
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
