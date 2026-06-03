"""
服务模块初始化

注意：sse_service 和 report_service 不在此处导出，
因为它们依赖 app.agents.orchestrator，会与 app.agents.base 形成循环导入。
需要使用时请直接从子模块导入：
  from app.services.sse_service import run_analysis_with_streaming
  from app.services.report_service import save_agent_outputs
"""
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.vector_store_service import VectorStoreService, get_vector_store_service
from app.services.rag_service import RAGService, get_rag_service

__all__ = [
    "EmbeddingService", "get_embedding_service",
    "KnowledgeService", "get_knowledge_service",
    "VectorStoreService", "get_vector_store_service",
    "RAGService", "get_rag_service"
]
