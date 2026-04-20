"""
知识库管理API端点
提供文档上传、文本导入、知识搜索、文档删除和集合列表等功能
"""
import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form, Query, Depends, HTTPException, status

from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeDocumentType,
    KnowledgeSearchResponse,
    KnowledgeSearchResult
)
from app.schemas.common import ApiResponse
from app.services.knowledge_service import get_knowledge_service
from app.services.vector_store_service import get_vector_store_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.post("/documents", response_model=ApiResponse[KnowledgeDocument])
async def upload_document(
    file: UploadFile = File(..., description="上传的文件"),
    title: str = Form(..., description="文档标题"),
    doc_type: KnowledgeDocumentType = Form(..., description="文档类型"),
    tags: str = Form(default="", description="逗号分隔的标签"),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传知识文档
    
    支持的文件格式：TXT、Markdown、PDF
    
    Args:
        file: 上传的文件
        title: 文档标题
        doc_type: 文档类型（analysis_report/investment_strategy/research_report/news）
        tags: 逗号分隔的标签字符串
        current_user: 当前登录用户
        
    Returns:
        上传成功的文档信息
    """
    # 检查文件扩展名
    allowed_extensions = [".txt", ".md", ".markdown", ".pdf"]
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
        )
    
    # 解析标签
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    # 创建临时文件保存上传的内容
    try:
        # 读取上传的文件内容
        content = await file.read()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # 使用知识库服务导入文档
            knowledge_service = get_knowledge_service()
            document_id = knowledge_service.import_document(
                file_path=temp_path,
                title=title,
                doc_type=doc_type,
                tags=tag_list,
                metadata={"uploader": current_user.username, "filename": file.filename}
            )
            
            # 获取文档详情
            doc_info = knowledge_service.get_document(document_id)
            
            if not doc_info:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="文档上传成功但获取详情失败"
                )
            
            # 构建响应
            document = KnowledgeDocument(
                id=doc_info["id"],
                title=doc_info["title"],
                content=doc_info["content"],
                doc_type=doc_info["doc_type"],
                tags=doc_info["tags"],
                metadata=doc_info["metadata"],
                created_at=doc_info["created_at"],
                updated_at=doc_info["updated_at"],
                chunk_count=doc_info["chunk_count"]
            )
            
            return ApiResponse(
                code=200,
                message="文档上传成功",
                data=document
            )
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传文档失败: {str(e)}"
        )


@router.post("/documents/text", response_model=ApiResponse[KnowledgeDocument])
async def import_text(
    request: KnowledgeDocumentCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    导入文本内容到知识库
    
    直接将文本内容导入知识库，无需上传文件
    
    Args:
        request: 文档创建请求，包含标题、内容、类型、标签和元数据
        current_user: 当前登录用户
        
    Returns:
        导入成功的文档信息
    """
    try:
        # 使用知识库服务导入文本
        knowledge_service = get_knowledge_service()
        
        # 添加创建者信息到元数据
        metadata = request.metadata or {}
        metadata["creator"] = current_user.username
        
        document_id = knowledge_service.import_text(
            content=request.content,
            title=request.title,
            doc_type=request.doc_type,
            tags=request.tags,
            metadata=metadata
        )
        
        # 获取文档详情
        doc_info = knowledge_service.get_document(document_id)
        
        if not doc_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文本导入成功但获取详情失败"
            )
        
        # 构建响应
        document = KnowledgeDocument(
            id=doc_info["id"],
            title=doc_info["title"],
            content=doc_info["content"],
            doc_type=doc_info["doc_type"],
            tags=doc_info["tags"],
            metadata=doc_info["metadata"],
            created_at=doc_info["created_at"],
            updated_at=doc_info["updated_at"],
            chunk_count=doc_info["chunk_count"]
        )
        
        return ApiResponse(
            code=200,
            message="文本导入成功",
            data=document
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"导入文本失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入文本失败: {str(e)}"
        )


@router.get("/search", response_model=ApiResponse[KnowledgeSearchResponse])
async def search_knowledge(
    query: str = Query(..., description="搜索查询关键词", min_length=1),
    top_k: int = Query(default=5, ge=1, le=20, description="返回结果数量"),
    doc_type: Optional[KnowledgeDocumentType] = Query(default=None, description="文档类型过滤"),
    tags: Optional[str] = Query(default=None, description="逗号分隔的标签过滤"),
    current_user: User = Depends(get_current_active_user)
):
    """
    搜索知识库
    
    使用向量相似度搜索知识库中的相关内容
    
    Args:
        query: 搜索查询关键词
        top_k: 返回结果数量，默认5，范围1-20
        doc_type: 可选的文档类型过滤
        tags: 可选的逗号分隔标签过滤
        current_user: 当前登录用户
        
    Returns:
        搜索结果列表
    """
    try:
        # 解析标签过滤
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        
        # 使用知识库服务搜索
        knowledge_service = get_knowledge_service()
        results = knowledge_service.search(
            query=query,
            doc_type=doc_type,
            tags=tag_list,
            top_k=top_k
        )
        
        # 构建搜索结果
        search_results = [
            KnowledgeSearchResult(
                content=result["content"],
                score=result["score"],
                metadata=result["metadata"],
                document_id=result["document_id"]
            )
            for result in results
        ]
        
        return ApiResponse(
            code=200,
            message="搜索成功",
            data=KnowledgeSearchResponse(
                results=search_results,
                total=len(search_results),
                query=query
            )
        )
        
    except Exception as e:
        logger.error(f"搜索知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    删除知识文档
    
    根据文档ID删除知识库中的文档
    
    Args:
        document_id: 要删除的文档ID
        current_user: 当前登录用户
        
    Returns:
        删除结果
    """
    try:
        # 使用知识库服务删除文档
        knowledge_service = get_knowledge_service()
        success = knowledge_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在或删除失败"
            )
        
        return ApiResponse(
            code=200,
            message="文档删除成功",
            data={"document_id": document_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )


@router.get("/collections")
async def list_collections(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取知识库集合列表
    
    列出向量数据库中所有的集合信息
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        集合列表，包含名称和文档数量
    """
    try:
        # 使用向量存储服务获取集合列表
        vector_store = get_vector_store_service()
        collection_names = vector_store.list_collections()
        
        # 获取每个集合的文档数量
        collections = []
        for name in collection_names:
            count = vector_store.get_collection_count(name)
            collections.append({
                "name": name,
                "document_count": count
            })
        
        return ApiResponse(
            code=200,
            message="获取集合列表成功",
            data={
                "collections": collections,
                "total": len(collections)
            }
        )
        
    except Exception as e:
        logger.error(f"获取集合列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取集合列表失败: {str(e)}"
        )
