"""
智能体基础类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio


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
            "duration_ms": self.duration_ms
        }
