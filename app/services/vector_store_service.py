"""
向量存储服务模块
使用 ChromaDB 实现向量数据库的存储和检索功能
支持基金知识库、分析案例库、投资策略库的向量检索
"""
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.core.settings_manager import get_settings_manager
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    向量存储服务类
    使用 ChromaDB 实现向量数据库功能
    支持文档的增删改查和相似度检索
    使用 lazy initialization 延迟初始化数据库连接
    """
    
    _instance: Optional["VectorStoreService"] = None
    _client: Optional[object] = None
    _embedding_service: Optional[object] = None
    
    FUND_KNOWLEDGE = "fund_knowledge"
    ANALYSIS_CASES = "analysis_cases"
    INVESTMENT_STRATEGY = "investment_strategy"
    
    def __new__(cls) -> "VectorStoreService":
        """
        单例模式，确保全局只有一个 ChromaDB 客户端实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化向量存储服务
        数据库连接延迟初始化，不在构造函数中建立连接
        """
        self._persist_dir = settings.CHROMA_PERSIST_DIR
        # 优先从 config.json 读取（前端可编辑），回退到 .env 配置
        sm = get_settings_manager()
        self._top_k = sm.get("rag.top_k", settings.RAG_TOP_K)
        self._collections: Dict[str, object] = {}
    
    def _initialize_client(self):
        """
        延迟初始化 ChromaDB 客户端
        只在第一次使用时建立数据库连接
        """
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            persist_path = Path(self._persist_dir)
            persist_path.mkdir(parents=True, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self._embedding_service = get_embedding_service()
    
    def _get_or_create_collection(self, name: str) -> Any:
        """
        获取或创建集合
        
        Args:
            name: 集合名称
            
        Returns:
            ChromaDB Collection 对象
        """
        self._initialize_client()
        
        if name not in self._collections:
            from chromadb.utils import embedding_functions
            
            class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
                """自定义 Embedding 函数，使用项目的 EmbeddingService"""
                
                def __init__(self, embedding_service):
                    self._embedding_service = embedding_service
                
                def __call__(self, input: List[str]) -> List[List[float]]:
                    return self._embedding_service.embed_documents(input)
            
            custom_ef = CustomEmbeddingFunction(self._embedding_service)
            
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=custom_ef,
                metadata={"hnsw:space": "cosine"}
            )
        
        return self._collections[name]
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到集合
        
        Args:
            collection_name: 集合名称
            documents: 文档内容列表
            metadatas: 元数据列表，每个元素对应一个文档
            ids: 文档 ID 列表，如果不提供则自动生成
            
        Returns:
            添加的文档 ID 列表
        """
        if not documents:
            return []
        
        self._initialize_client()
        collection = self._get_or_create_collection(collection_name)
        
        import uuid
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        for i, doc in enumerate(documents):
            if not metadatas[i]:
                metadatas[i] = {"source": "user_upload", "doc_index": i}
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: Optional[int] = None,
        where: Optional[dict] = None
    ) -> dict:
        """
        查询相似文档
        
        Args:
            collection_name: 集合名称
            query_text: 查询文本
            n_results: 返回结果数量，默认使用配置的 RAG_TOP_K
            where: 元数据过滤条件，例如 {"source": "user_upload"}
            
        Returns:
            包含查询结果的字典，包括 documents, metadatas, distances, ids
        """
        if not query_text or not query_text.strip():
            return {
                "documents": [],
                "metadatas": [],
                "distances": [],
                "ids": []
            }
        
        self._initialize_client()
        collection = self._get_or_create_collection(collection_name)
        
        if n_results is None:
            n_results = self._top_k
        
        query_params = {
            "query_texts": [query_text],
            "n_results": n_results
        }
        
        if where:
            query_params["where"] = where
        
        results = collection.query(**query_params)
        
        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
            "ids": results.get("ids", [[]])[0]
        }
    
    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """
        删除文档
        
        Args:
            collection_name: 集合名称
            ids: 要删除的文档 ID 列表
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        if not ids:
            return False
        
        self._initialize_client()
        
        try:
            collection = self._get_or_create_collection(collection_name)
            collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        self._initialize_client()
        
        try:
            self._client.delete_collection(name=collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name]
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        Returns:
            集合名称列表
        """
        self._initialize_client()
        
        collections = self._client.list_collections()
        return [collection.name for collection in collections]
    
    def get_collection_count(self, collection_name: str) -> int:
        """
        获取集合中文档数量
        
        Args:
            collection_name: 集合名称
            
        Returns:
            文档数量
        """
        self._initialize_client()
        
        try:
            collection = self._get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"获取集合文档数量失败: {e}")
            return 0
    
    def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        更新文档
        
        Args:
            collection_name: 集合名称
            document_id: 文档 ID
            document: 新的文档内容
            metadata: 新的元数据
            
        Returns:
            更新成功返回 True，失败返回 False
        """
        self._initialize_client()
        
        try:
            collection = self._get_or_create_collection(collection_name)
            
            update_params = {
                "ids": [document_id],
                "documents": [document]
            }
            
            if metadata:
                update_params["metadatas"] = [metadata]
            
            collection.update(**update_params)
            return True
        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            return False
    
    def get_document_by_id(
        self,
        collection_name: str,
        document_id: str
    ) -> Optional[dict]:
        """
        根据 ID 获取文档
        
        Args:
            collection_name: 集合名称
            document_id: 文档 ID
            
        Returns:
            文档信息字典，包含 document, metadata, id；如果不存在返回 None
        """
        self._initialize_client()
        
        try:
            collection = self._get_or_create_collection(collection_name)
            result = collection.get(ids=[document_id])
            
            if result and result.get("ids"):
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result.get("documents") else None,
                    "metadata": result["metadatas"][0] if result.get("metadatas") else {}
                }
            return None
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None
    
    def get_by_metadata(
        self,
        collection_name: str,
        where: dict,
        limit: int = 1000
    ) -> dict:
        """
        根据元数据条件获取文档（不使用语义查询）
        
        Args:
            collection_name: 集合名称
            where: 元数据过滤条件
            limit: 返回结果数量限制
            
        Returns:
            包含查询结果的字典，包括 documents, metadatas, ids
        """
        self._initialize_client()
        
        try:
            collection = self._get_or_create_collection(collection_name)
            result = collection.get(
                where=where,
                limit=limit
            )
            
            return {
                "documents": result.get("documents", []),
                "metadatas": result.get("metadatas", []),
                "ids": result.get("ids", [])
            }
        except Exception as e:
            logger.error(f"根据元数据获取文档失败: {e}")
            return {
                "documents": [],
                "metadatas": [],
                "ids": []
            }
    
    def reset_database(self) -> bool:
        """
        重置整个向量数据库
        删除所有集合和数据
        
        Returns:
            重置成功返回 True，失败返回 False
        """
        self._initialize_client()
        
        try:
            self._client.reset()
            self._collections.clear()
            return True
        except Exception as e:
            logger.error(f"重置数据库失败: {e}")
            return False


@lru_cache()
def get_vector_store_service() -> VectorStoreService:
    """
    获取向量存储服务单例
    
    Returns:
        VectorStoreService 实例
    """
    return VectorStoreService()
