"""
智能体基础类

提供LLM驱动的智能体基类，支持工具调用和知识增强
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timezone
import json
import logging
import asyncio

from app.services.rag_service import get_rag_service
from app.services.llm_service import get_llm_service
from app.agents.tools.base import ToolRegistry, ToolResult
from app.agents.prompts import get_prompt_template

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    智能体基类
    
    支持LLM驱动的分析流程，包括：
    - 系统提示词模板
    - 工具调用机制
    - RAG知识增强
    - 结构化输出解析
    """
    
    def __init__(self, agent_type: str, name: str):
        """
        初始化智能体
        
        Args:
            agent_type: 智能体类型标识
            name: 智能体显示名称
        """
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
        
        self._rag_context: List[str] = []
        self._llm_service = None
        self._tool_registry = None
        self._prompt_template = None
        self._thinking_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self._tool_call_callback: Optional[Callable[[str, Dict[str, Any], Optional[Dict[str, Any]], str], Awaitable[None]]] = None
    
    def set_thinking_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        设置思考过程回调函数
        
        Args:
            callback: 异步回调函数，接收思考内容
        """
        self._thinking_callback = callback
    
    def set_tool_call_callback(
        self, 
        callback: Optional[Callable[[str, Dict[str, Any], Optional[Dict[str, Any]], str], Awaitable[None]]]
    ) -> None:
        """
        设置工具调用回调函数
        
        Args:
            callback: 异步回调函数，接收工具名称、参数、结果和状态
        """
        self._tool_call_callback = callback
    
    async def add_thinking(self, content: str) -> None:
        """
        添加思考过程
        
        Args:
            content: 思考内容
        """
        self.thinking_process.append({
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "text": content
        })
        
        if self._thinking_callback:
            await self._thinking_callback(content)
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Optional[ToolResult] = None) -> None:
        """
        添加工具调用记录
        
        Args:
            tool_name: 工具名称
            args: 调用参数
            result: 执行结果
        """
        result_dict = result.to_dict() if result else None
        status = "success" if result and result.success else "failed" if result else "pending"
        
        self.tools_called.append({
            "name": tool_name,
            "args": args,
            "result": result_dict,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if self._tool_call_callback:
            import asyncio
            asyncio.create_task(
                self._tool_call_callback(tool_name, args, result_dict, status)
            )
    
    def get_system_prompt(self) -> str:
        """
        获取系统提示词
        
        Returns:
            系统提示词字符串
        """
        if self._prompt_template is None:
            self._prompt_template = get_prompt_template(self.agent_type)
        
        if self._prompt_template:
            return self._prompt_template.get_system_prompt()
        
        return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """
        获取默认系统提示词（子类可覆盖）
        
        Returns:
            默认系统提示词
        """
        return f"""你是一位专业的{name}，负责分析基金投资相关的数据。

请基于提供的数据进行专业分析，并输出结构化的分析结果。"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            OpenAI格式的工具定义列表
        """
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry()
        
        from app.agents.tools import get_tools_for_agent
        tool_names = get_tools_for_agent(self.agent_type)
        
        tools = []
        for tool_name in tool_names:
            tool = self._tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool.to_openai_tool())
        
        return tools
    
    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        use_tools: bool = True
    ) -> str:
        """
        调用LLM服务
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选，默认使用get_system_prompt）
            temperature: 温度参数
            use_tools: 是否启用工具调用
            
        Returns:
            LLM响应文本
        """
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        
        if system_prompt is None:
            system_prompt = self.get_system_prompt()
        
        await self.add_thinking("正在调用大语言模型进行分析...")
        
        if use_tools and self.get_tools():
            response = await self._call_llm_with_tools(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
        else:
            response = await self._llm_service.chat_async(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
        
        return response
    
    async def _call_llm_with_tools(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_iterations: int = 5
    ) -> str:
        """
        带工具调用的LLM请求
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_iterations: 最大迭代次数
            
        Returns:
            最终响应文本
        """
        client = self._llm_service.get_async_client()
        model = self._llm_service.get_model_name()
        tools = self.get_tools()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        for iteration in range(max_iterations):
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
            
            message = response.choices[0].message
            
            if message.content:
                messages.append({"role": "assistant", "content": message.content})
            
            if message.tool_calls:
                messages.append(message)
                
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    await self.add_thinking(f"调用工具: {tool_name}")
                    
                    result = await self.execute_tool(tool_name, tool_args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result.to_dict(), ensure_ascii=False)
                    })
            else:
                return message.content or ""
        
        return messages[-1].get("content", "") if messages else ""
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry()
        
        result = await self._tool_registry.execute_tool(tool_name, params)
        
        self.add_tool_call(tool_name, params, result)
        
        if result.success:
            await self.add_thinking(f"工具 {tool_name} 执行成功")
        else:
            await self.add_thinking(f"工具 {tool_name} 执行失败: {result.error}")
        
        return result
    
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
        await self.add_thinking(f"正在检索相关知识: {query[:50]}...")
        rag_service = get_rag_service()
        results = rag_service.retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            filters=filters
        )
        if results:
            await self.add_thinking(f"检索到 {len(results)} 条相关知识")
        return results

    async def build_rag_context(
        self,
        query: str,
        collection_name: str = "fund_knowledge",
        context_type: str = "general"
    ) -> str:
        """
        构建RAG增强上下文
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            context_type: 上下文类型
            
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
    
    def build_context_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建上下文提示词
        
        Args:
            context: 分析上下文数据
            
        Returns:
            格式化的上下文提示词
        """
        if self._prompt_template is None:
            self._prompt_template = get_prompt_template(self.agent_type)
        
        if self._prompt_template:
            return self._prompt_template.get_user_prompt(context)
        
        return self._build_default_context_prompt(context)
    
    def _build_default_context_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建默认上下文提示词
        
        Args:
            context: 分析上下文
            
        Returns:
            默认上下文提示词
        """
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        
        prompt = f"""请分析以下基金数据：

{context_str}

请基于以上数据进行专业分析，并输出结构化的分析结果。"""
        
        if self._rag_context:
            knowledge_str = "\n\n".join(self._rag_context)
            prompt += f"""

【相关知识】
{knowledge_str}"""
        
        return prompt
    
    def parse_llm_output(self, llm_response: str) -> Dict[str, Any]:
        """
        解析LLM输出为结构化结果
        
        Args:
            llm_response: LLM响应文本
            
        Returns:
            解析后的结果字典
        """
        try:
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                result = json.loads(json_str)
                
                self.score = result.get("score")
                self.summary = result.get("summary")
                self.details = result.get("details", {})
                
                return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
        
        return self._parse_fallback(llm_response)
    
    def _parse_fallback(self, llm_response: str) -> Dict[str, Any]:
        """
        解析失败时的降级处理
        
        Args:
            llm_response: LLM响应文本
            
        Returns:
            降级处理后的结果
        """
        self.summary = llm_response[:200] if len(llm_response) > 200 else llm_response
        self.details = {"raw_response": llm_response}
        
        return {
            "score": None,
            "summary": self.summary,
            "details": self.details,
            "parse_error": True
        }
    
    @abstractmethod
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析（子类实现）
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            
        Returns:
            分析结果字典
        """
        pass
    
    async def run_llm_analysis(
        self,
        fund_code: str,
        context: Dict[str, Any],
        use_rag: bool = True,
        use_tools: bool = True
    ) -> Dict[str, Any]:
        """
        执行LLM驱动的分析流程
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            use_rag: 是否使用RAG知识增强
            use_tools: 是否使用工具调用
            
        Returns:
            分析结果字典
        """
        context["fund_code"] = fund_code
        
        if use_rag:
            rag_context = await self.build_rag_context(
                query=f"{self.agent_type}分析 {fund_code}",
                context_type=self.agent_type
            )
            if rag_context:
                context["rag_knowledge"] = rag_context
        
        prompt = self.build_context_prompt(context)
        
        llm_response = await self.call_llm(
            prompt=prompt,
            use_tools=use_tools
        )
        
        result = self.parse_llm_output(llm_response)
        
        return result
    
    async def run(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行智能体
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            
        Returns:
            分析结果字典
        """
        self.started_at = datetime.now(timezone.utc)
        self.status = "running"
        
        try:
            result = await self.analyze(fund_code, context)
            self.status = "completed"
            self.completed_at = datetime.now(timezone.utc)
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
            return result
        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            self.completed_at = datetime.now(timezone.utc)
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            智能体状态字典
        """
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
