"""
知识库服务模块
提供文档导入、解析、分块和检索功能
支持 TXT、Markdown、PDF 等多种文档格式
"""
from loguru import logger
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.settings_manager import get_settings_manager
from app.schemas.knowledge import KnowledgeDocumentType
from app.services.vector_store_service import get_vector_store_service

class KnowledgeService:
    """
    知识库服务类
    提供文档导入、解析、分块和检索功能
    """
    
    KNOWLEDGE_COLLECTION = "fund_knowledge"
    
    def __init__(self):
        """
        初始化知识库服务
        获取向量存储服务实例
        """
        self._vector_store = get_vector_store_service()
        # 优先从 config.json 读取（前端可编辑），回退到 .env 配置
        sm = get_settings_manager()
        self._chunk_size = sm.get("rag.chunk_size", settings.RAG_CHUNK_SIZE)
        self._chunk_overlap = sm.get("rag.chunk_overlap", settings.RAG_CHUNK_OVERLAP)
    
    def _parse_text_file(self, file_path: str) -> str:
        """
        解析 TXT 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容文本
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return content.strip()
    
    def _parse_markdown_file(self, file_path: str) -> str:
        """
        解析 Markdown 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容文本
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return content.strip()
    
    def _parse_pdf_file(self, file_path: str) -> str:
        """
        解析 PDF 文件
        使用 pdfplumber 解析 PDF 文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容文本
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n\n".join(text_parts).strip()
        except ImportError:
            raise ImportError("请安装 pdfplumber: pip install pdfplumber")
    
    def _split_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[str]:
        """
        文档分块
        使用 langchain 的 RecursiveCharacterTextSplitter 进行分块
        
        Args:
            text: 待分块的文本
            chunk_size: 分块大小，默认使用配置值
            chunk_overlap: 分块重叠大小，默认使用配置值
            
        Returns:
            分块后的文本列表
        """
        if not text or not text.strip():
            return []
        
        actual_chunk_size = chunk_size or self._chunk_size
        actual_chunk_overlap = chunk_overlap or self._chunk_overlap
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=actual_chunk_size,
            chunk_overlap=actual_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        
        chunks = text_splitter.split_text(text)
        return chunks
    
    def _get_file_extension(self, file_path: str) -> str:
        """
        获取文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件扩展名（小写）
        """
        return Path(file_path).suffix.lower()
    
    def _parse_file(self, file_path: str) -> str:
        """
        根据文件类型解析文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容文本
        """
        ext = self._get_file_extension(file_path)
        
        parsers = {
            ".txt": self._parse_text_file,
            ".md": self._parse_markdown_file,
            ".markdown": self._parse_markdown_file,
            ".pdf": self._parse_pdf_file
        }
        
        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        return parser(file_path)
    
    def import_document(
        self,
        file_path: str,
        title: str,
        doc_type: KnowledgeDocumentType,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        导入文档
        
        Args:
            file_path: 文件路径
            title: 文档标题
            doc_type: 文档类型
            tags: 标签列表
            metadata: 元数据
            
        Returns:
            文档 ID
        """
        content = self._parse_file(file_path)
        
        return self.import_text(
            content=content,
            title=title,
            doc_type=doc_type,
            tags=tags,
            metadata=metadata
        )
    
    def import_text(
        self,
        content: str,
        title: str,
        doc_type: KnowledgeDocumentType,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        导入文本内容
        
        Args:
            content: 文本内容
            title: 文档标题
            doc_type: 文档类型
            tags: 标签列表
            metadata: 元数据
            
        Returns:
            文档 ID
        """
        if not content or not content.strip():
            raise ValueError("内容不能为空")
        
        document_id = str(uuid.uuid4())
        chunks = self._split_text(content)
        
        if not chunks:
            raise ValueError("文档分块失败，内容可能为空")
        
        now = datetime.now(timezone.utc)
        tags = tags or []
        metadata = metadata or {}
        
        base_metadata = {
            "document_id": document_id,
            "title": title,
            "doc_type": doc_type.value,
            "tags": ",".join(tags) if tags else "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            **metadata
        }
        
        chunk_metadatas = []
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {**base_metadata, "chunk_index": i}
            chunk_metadatas.append(chunk_metadata)
            chunk_ids.append(f"{document_id}_chunk_{i}")
        
        self._vector_store.add_documents(
            collection_name=self.KNOWLEDGE_COLLECTION,
            documents=chunks,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )
        
        return document_id
    
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档 ID
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        try:
            results = self._vector_store.get_by_metadata(
                collection_name=self.KNOWLEDGE_COLLECTION,
                where={"document_id": document_id}
            )
            
            if not results.get("ids"):
                return False
            
            return self._vector_store.delete_documents(
                collection_name=self.KNOWLEDGE_COLLECTION,
                ids=results["ids"]
            )
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def search(
        self,
        query: str,
        doc_type: Optional[KnowledgeDocumentType] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        搜索知识
        
        Args:
            query: 搜索查询
            doc_type: 文档类型过滤
            tags: 标签过滤
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表，每项包含 content, score, metadata, document_id
        """
        where_filter = {}
        
        if doc_type:
            where_filter["doc_type"] = doc_type.value
        
        if tags and len(tags) == 1:
            where_filter["tags"] = tags[0]
        
        results = self._vector_store.query(
            collection_name=self.KNOWLEDGE_COLLECTION,
            query_text=query,
            n_results=top_k,
            where=where_filter if where_filter else None
        )
        
        search_results = []
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        distances = results.get("distances", [])
        ids = results.get("ids", [])
        
        for i in range(len(documents)):
            if tags and len(tags) > 1:
                doc_tags = metadatas[i].get("tags", "")
                doc_tags_list = doc_tags.split(",") if doc_tags else []
                if not any(tag in doc_tags_list for tag in tags):
                    continue
            
            score = 1 - distances[i] if i < len(distances) else 0.0
            
            search_results.append({
                "content": documents[i],
                "score": score,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "document_id": metadatas[i].get("document_id", "") if i < len(metadatas) else ""
            })
        
        return search_results[:top_k]
    
    def get_document(self, document_id: str) -> Optional[dict]:
        """
        获取文档详情
        
        Args:
            document_id: 文档 ID
            
        Returns:
            文档详情字典，包含 id, title, content, doc_type, tags, metadata, chunk_count 等
        """
        try:
            results = self._vector_store.query(
                collection_name=self.KNOWLEDGE_COLLECTION,
                query_text="",
                n_results=1000,
                where={"document_id": document_id}
            )
            
            if not results.get("ids"):
                return None
            
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents or not metadatas:
                return None
            
            sorted_chunks = sorted(
                zip(documents, metadatas),
                key=lambda x: x[1].get("chunk_index", 0)
            )
            
            full_content = "\n".join([chunk[0] for chunk in sorted_chunks])
            first_metadata = sorted_chunks[0][1] if sorted_chunks else {}
            
            tags_str = first_metadata.get("tags", "")
            tags = tags_str.split(",") if tags_str else []
            
            doc_type_value = first_metadata.get("doc_type", "")
            try:
                doc_type = KnowledgeDocumentType(doc_type_value)
            except ValueError:
                doc_type = None
            
            return {
                "id": document_id,
                "title": first_metadata.get("title", ""),
                "content": full_content,
                "doc_type": doc_type,
                "tags": tags,
                "metadata": {k: v for k, v in first_metadata.items() 
                           if k not in ["document_id", "title", "doc_type", "tags", "chunk_index"]},
                "chunk_count": len(documents),
                "created_at": first_metadata.get("created_at", ""),
                "updated_at": first_metadata.get("updated_at", "")
            }
        except Exception as e:
            logger.error(f"获取文档详情失败: {e}")
            return None

def get_knowledge_service() -> KnowledgeService:
    """
    获取知识库服务实例
    
    Returns:
        KnowledgeService 实例
    """
    return KnowledgeService()
