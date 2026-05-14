"""
RAG (Retrieval-Augmented Generation) 服务模块
提供知识检索和上下文构建功能，支持多智能体场景的知识增强
"""
from typing import List, Optional, Dict, Any
from functools import lru_cache
import logging

from app.core.config import settings
from app.services.vector_store_service import get_vector_store_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG 服务类
    封装向量检索、上下文构建和重排序功能
    为智能体提供知识增强支持
    """
    
    CONTEXT_TYPE_PROMPTS = {
        "fundamental": "基本面分析相关知识",
        "technical": "技术面分析相关知识",
        "risk": "风险评估相关知识",
        "sentiment": "市场情绪分析相关知识",
        "decision": "投资决策相关知识",
        "general": "基金投资相关知识"
    }
    
    def __init__(self):
        """
        初始化 RAG 服务
        获取向量存储服务实例和配置参数
        """
        self._vector_store = get_vector_store_service()
        self._default_top_k = settings.RAG_TOP_K
        self._embedding_checked = False
        self._embedding_configured = None
    
    def _is_embedding_configured(self) -> bool:
        """
        检查 Embedding 是否已配置

        使用缓存避免重复检查配置。

        Returns:
            True 表示已配置，False 表示未配置
        """
        if not self._embedding_checked:
            from app.core.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()
            self._embedding_configured = settings_manager.is_embedding_configured()
            self._embedding_checked = True
            if not self._embedding_configured:
                logger.info("RAG服务: Embedding 未配置，知识检索功能已禁用")
        return self._embedding_configured
    
    def retrieve(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        top_k: Optional[int] = None,
        filters: Optional[dict] = None
    ) -> List[dict]:
        """
        语义相似度检索
        
        Args:
            query: 查询文本
            collection_name: 集合名称，默认为 fund_knowledge
            top_k: 返回结果数量，默认使用配置的 RAG_TOP_K
            filters: 元数据过滤条件，例如 {"source": "analysis_report"}
            
        Returns:
            检索结果列表，格式为:
            [{"content": str, "score": float, "metadata": dict, "document_id": str}, ...]
        """
        # 检查 embedding 是否已配置
        if not self._is_embedding_configured():
            return []
        
        if not query or not query.strip():
            return []
        
        if top_k is None:
            top_k = self._default_top_k
        
        results = self._vector_store.query(
            collection_name=collection_name,
            query_text=query,
            n_results=top_k,
            where=filters
        )
        
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        distances = results.get("distances", [])
        ids = results.get("ids", [])
        
        retrieved_results = []
        for i in range(len(documents)):
            distance = distances[i] if i < len(distances) else 1.0
            score = 1.0 - distance
            
            result = {
                "content": documents[i] if i < len(documents) else "",
                "score": round(score, 4),
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "document_id": ids[i] if i < len(ids) else ""
            }
            retrieved_results.append(result)
        
        return retrieved_results
    
    def build_context(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        context_type: str = "general"
    ) -> str:
        """
        构建 RAG 增强上下文
        
        将检索结果格式化为 LLM 可用的上下文字符串
        
        Args:
            query: 查询文本
            collection_name: 集合名称，默认为 fund_knowledge
            context_type: 上下文类型，支持:
                - "fundamental": 基本面分析
                - "technical": 技术面分析
                - "risk": 风险评估
                - "sentiment": 市场情绪
                - "decision": 投资决策
                - "general": 通用（默认）
                
        Returns:
            格式化的上下文字符串，格式示例:
            【相关知识】
            1. [来源: 分析报告] 内容摘要...
            2. [来源: 投资策略] 内容摘要...
            ...
        """
        if not query or not query.strip():
            return ""
        
        context_prompt = self.CONTEXT_TYPE_PROMPTS.get(
            context_type, 
            self.CONTEXT_TYPE_PROMPTS["general"]
        )
        
        results = self.retrieve(
            query=query,
            collection_name=collection_name,
            top_k=self._default_top_k
        )
        
        if not results:
            return ""
        
        context_lines = [f"【{context_prompt}】"]
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)
            
            source = metadata.get("source", "知识库")
            source_type = metadata.get("type", "")
            
            if source_type:
                source_display = f"{source} - {source_type}"
            else:
                source_display = source
            
            max_content_length = 300
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            context_lines.append(
                f"{i}. [来源: {source_display}] [相关度: {score:.2f}] {content}"
            )
        
        return "\n".join(context_lines)
    
    def retrieve_and_rerank(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        top_k: int = 10,
        final_k: int = 5
    ) -> List[dict]:
        """
        检索并重排序
        
        先检索 top_k 个结果，然后根据相关性重排序返回 final_k 个
        
        Args:
            query: 查询文本
            collection_name: 集合名称，默认为 fund_knowledge
            top_k: 初始检索数量，默认为 10
            final_k: 最终返回数量，默认为 5
            
        Returns:
            重排序后的检索结果列表
        """
        if not query or not query.strip():
            return []
        
        results = self.retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k
        )
        
        if not results:
            return []
        
        reranked_results = self._rerank_by_relevance(query, results)
        
        return reranked_results[:final_k]
    
    def _rerank_by_relevance(
        self,
        query: str,
        results: List[dict]
    ) -> List[dict]:
        """
        基于相关性对检索结果进行重排序
        
        综合考虑向量相似度分数和关键词匹配度
        
        Args:
            query: 原始查询文本
            results: 原始检索结果列表
            
        Returns:
            重排序后的结果列表
        """
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        scored_results = []
        for result in results:
            base_score = result.get("score", 0)
            
            content = result.get("content", "").lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in content)
            keyword_bonus = keyword_matches / max(len(query_keywords), 1) * 0.2
            
            metadata = result.get("metadata", {})
            recency_bonus = 0
            if "importance" in metadata:
                importance = metadata["importance"]
                if isinstance(importance, (int, float)):
                    recency_bonus = min(importance / 10, 0.1)
            
            final_score = base_score + keyword_bonus + recency_bonus
            result_copy = result.copy()
            result_copy["reranked_score"] = round(final_score, 4)
            scored_results.append(result_copy)
        
        scored_results.sort(key=lambda x: x.get("reranked_score", 0), reverse=True)
        
        return scored_results
    
    def get_context_for_agent(
        self,
        agent_type: str,
        query: str,
        collection_name: str = "fund_knowledge"
    ) -> str:
        """
        为特定类型的智能体获取上下文
        
        根据智能体类型自动选择合适的上下文类型
        
        Args:
            agent_type: 智能体类型，如 "fundamental", "technical", "risk" 等
            query: 查询文本
            collection_name: 集合名称
            
        Returns:
            格式化的上下文字符串
        """
        context_type_map = {
            "fundamental": "fundamental",
            "technical": "technical",
            "risk": "risk",
            "sentiment": "sentiment",
            "decision": "decision",
            "cost": "general",
            "emotion": "sentiment"
        }
        
        context_type = context_type_map.get(agent_type, "general")
        
        return self.build_context(
            query=query,
            collection_name=collection_name,
            context_type=context_type
        )
    
    def batch_retrieve(
        self,
        queries: List[str],
        collection_name: str = "fund_knowledge",
        top_k: Optional[int] = None
    ) -> Dict[str, List[dict]]:
        """
        批量检索
        
        对多个查询同时进行检索，返回每个查询的结果
        
        Args:
            queries: 查询文本列表
            collection_name: 集合名称
            top_k: 每个查询返回的结果数量
            
        Returns:
            字典，键为查询文本，值为检索结果列表
        """
        results = {}
        for query in queries:
            if query and query.strip():
                results[query] = self.retrieve(
                    query=query,
                    collection_name=collection_name,
                    top_k=top_k
                )
            else:
                results[query] = []
        
        return results

    def reset_config_cache(self) -> None:
        """
        重置配置缓存

        当用户更新 Embedding 配置后调用此方法，
        使 RAG 服务能够重新检测配置状态。
        """
        self._embedding_checked = False
        self._embedding_configured = None
        logger.info("RAG服务: 配置缓存已重置")


@lru_cache()
def get_rag_service() -> RAGService:
    """
    获取 RAG 服务单例
    
    Returns:
        RAGService 实例
    """
    return RAGService()
