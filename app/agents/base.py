"""
智能体基础类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from app.services.rag_service import get_rag_service


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_type: str, name: str):
        self.agent_type = agent_type
        self.name = name
        self.status = "pending"
        self.score: Optional[float] = None
        self.summary: Optional[str] = None
        self.details: Dict[str, Any] = {}
        self.thinking_process: list = []
        self.tools_called: list = []
        self.error_message: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.duration_ms: Optional[int] = None
        # RAG 上下文存储
        self._rag_context: List[str] = []
    
    def add_thinking(self, content: str):
        """添加思考过程"""
        self.thinking_process.append({
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "text": content
        })
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """添加工具调用记录"""
        self.tools_called.append({
            "name": tool_name,
            "args": args,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def retrieve_knowledge(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        top_k: int = 5,
        filters: dict = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            top_k: 返回数量
            filters: 元数据过滤条件
            
        Returns:
            检索结果列表
        """
        self.add_thinking(f"正在检索相关知识: {query[:50]}...")
        rag_service = get_rag_service()
        results = rag_service.retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            filters=filters
        )
        if results:
            self.add_thinking(f"检索到 {len(results)} 条相关知识")
        return results

    async def build_rag_context(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        context_type: str = "general"
    ) -> str:
        """
        构建 RAG 增强上下文
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            context_type: 上下文类型（fundamental/technical/risk/sentiment/decision/general）
            
        Returns:
            格式化的上下文字符串
        """
        rag_service = get_rag_service()
        context = rag_service.build_context(
            query=query,
            collection_name=collection_name,
            context_type=context_type
        )
        return context
    
    @abstractmethod
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析"""
        pass
    
    async def run(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行智能体"""
        self.started_at = datetime.utcnow()
        self.status = "running"
        
        try:
            result = await self.analyze(fund_code, context)
            self.status = "completed"
            self.completed_at = datetime.utcnow()
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
            return result
        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            self.completed_at = datetime.utcnow()
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_type": self.agent_type,
            "name": self.name,
            "status": self.status,
            "score": self.score,
            "summary": self.summary,
            "details": self.details,
            "thinking_process": self.thinking_process,
            "tools_called": self.tools_called,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "rag_context": self._rag_context
        }
