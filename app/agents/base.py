"""
智能体基础类

提供LLM驱动的智能体基类，支持工具调用和知识增强
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, date, timezone
import json
from loguru import logger
import asyncio
import uuid
import random

from app.services.rag_service import get_rag_service
from app.services.llm_service import get_llm_service
from app.agents.tools.base import ToolRegistry, ToolResult
from app.agents.prompts import get_prompt_template
from app.agents.tools import get_tool_chinese_name
from openai import PermissionDeniedError, RateLimitError, APIError

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
        self.confidence: Optional[int] = None
        self.data_sufficiency: str = "unknown"
        self.data_sufficient: bool = True
        
        self._rag_context: List[str] = []
        self._llm_service = None
        self._tool_registry = None
        self._prompt_template = None
        self._thinking_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self._streaming_thinking_callback: Optional[Callable[[str, str, str, bool], Awaitable[None]]] = None
        self._tool_call_callback: Optional[Callable[[str, Dict[str, Any], Optional[Dict[str, Any]], str], Awaitable[None]]] = None
        self._streaming_buffer: Dict[str, str] = {}  # thinking_id -> 累积的思考内容
    
    def set_thinking_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        设置思考过程回调函数
        
        Args:
            callback: 异步回调函数，接收思考内容
        """
        self._thinking_callback = callback
    
    def set_streaming_thinking_callback(self, callback: Callable[[str, str, str, bool], Awaitable[None]]) -> None:
        """
        设置流式思考回调函数

        Args:
            callback: 异步回调函数，接收 (thinking_id, chunk_content, thinking_type, is_complete)
        """
        self._streaming_thinking_callback = callback
    
    async def add_streaming_thinking(self, thinking_id: str, chunk_content: str, thinking_type: str = "normal", is_complete: bool = False) -> None:
        """
        流式追加思考内容到当前思考段落

        Args:
            thinking_id: 思考段落的唯一标识
            chunk_content: 本次追加的思考内容片段
            thinking_type: 思考类型，支持 "normal"（普通思考）和 "deep_thinking"（深度思考）
            is_complete: 是否完成
        """
        # 如果是新的 thinking_id，初始化缓冲区并添加思考记录
        if thinking_id not in self._streaming_buffer:
            self._streaming_buffer[thinking_id] = ""
            thinking_record = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": chunk_content,
                "thinking_id": thinking_id,
                "thinking_type": thinking_type
            }
            self.thinking_process.append(thinking_record)

        # 累积内容（仅当有内容时）
        if chunk_content:
            self._streaming_buffer[thinking_id] += chunk_content

        # 更新 thinking_process 中的最后一条对应记录
        for record in reversed(self.thinking_process):
            if record.get("thinking_id") == thinking_id:
                record["text"] = self._streaming_buffer[thinking_id]
                break

        # 推送流式思考事件
        if self._streaming_thinking_callback:
            await self._streaming_thinking_callback(thinking_id, chunk_content, thinking_type, is_complete)
    
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
    
    def _handle_llm_error(self, error: Exception) -> str:
        """
        处理 LLM API 调用错误，将技术错误转换为用户友好提示
        
        Args:
            error: 原始异常对象
            
        Returns:
            用户友好的错误提示信息
        """
        error_str = str(error)
        
        # 403 配额耗尽错误
        if isinstance(error, PermissionDeniedError):
            if "AllocationQuota" in error_str or "free tier" in error_str.lower():
                logger.error(f"智能体 {self.name} LLM 配额已耗尽")
                return "LLM 服务配额已耗尽，请联系管理员或更换 API Key"
            logger.error(f"智能体 {self.name} LLM 权限被拒绝: {error_str[:200]}")
            return "LLM 服务权限不足，请联系管理员"
        
        # 429 限流错误
        if isinstance(error, RateLimitError):
            logger.error(f"智能体 {self.name} LLM 请求被限流")
            return "LLM 服务请求过于频繁，请稍后重试"
        
        # 其他 API 错误
        if isinstance(error, APIError):
            status_code = getattr(error, 'status_code', None)
            if status_code == 403:
                if "AllocationQuota" in error_str or "free tier" in error_str.lower():
                    return "LLM 服务配额已耗尽，请联系管理员或更换 API Key"
                return "LLM 服务权限不足，请联系管理员"
            if status_code == 429:
                return "LLM 服务请求过于频繁，请稍后重试"
            if status_code and status_code >= 500:
                return "LLM 服务暂时不可用，请稍后重试"
            logger.error(f"智能体 {self.name} LLM API 错误: {error_str[:200]}")
            return f"LLM 服务调用失败，请稍后重试"
        
        # 未知错误
        logger.error(f"智能体 {self.name} 未知 LLM 错误: {error_str[:200]}")
        return "分析服务暂时不可用，请稍后重试"
    
    async def add_thinking(self, content: str, thinking_id: Optional[str] = None, thinking_type: str = "normal") -> None:
        """
        添加思考过程
        
        Args:
            content: 思考内容
            thinking_id: 思考段落的唯一标识，如果不提供则自动生成
            thinking_type: 思考类型，支持 "normal"（普通思考）和 "deep_thinking"（深度思考）
        """
        if thinking_id is None:
            thinking_id = str(uuid.uuid4())
        
        thinking_record = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": content,
            "thinking_id": thinking_id,
            "thinking_type": thinking_type
        }
        self.thinking_process.append(thinking_record)
        
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
            "time": datetime.now().strftime("%H:%M:%S"),
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
        
        # 验证 prompt 不为空
        if not prompt or not prompt.strip():
            logger.warning(f"智能体 {self.name} 收到空的 prompt，使用默认提示")
            prompt = "请进行分析"
        
        await self.add_thinking("正在调用大语言模型进行分析...")
        
        try:
            if use_tools and self.get_tools():
                response = await self._call_llm_with_tools(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
            else:
                # 非工具路径：加入限流重试逻辑
                max_retries = 3
                for attempt in range(max_retries + 1):
                    try:
                        response = await self._llm_service.chat_async(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            temperature=temperature
                        )
                        break
                    except RateLimitError as e:
                        if attempt >= max_retries:
                            raise
                        delay = min(2.0 * (2 ** attempt) + random.uniform(0, 1), 30)
                        await self.add_thinking(
                            f"LLM 请求被限流，{delay:.0f}秒后自动重试（第 {attempt + 1}/{max_retries} 次）..."
                        )
                        logger.warning(
                            f"智能体 {self.name} LLM 请求被限流，"
                            f"{delay:.1f}秒后重试（第 {attempt + 1}/{max_retries} 次）"
                        )
                        await asyncio.sleep(delay)

            return response
        except (PermissionDeniedError, RateLimitError, APIError) as e:
            friendly_msg = self._handle_llm_error(e)
            self.error_message = friendly_msg
            raise
        except Exception as e:
            friendly_msg = self._handle_llm_error(e)
            self.error_message = friendly_msg
            raise
    
    async def _call_llm_with_tools(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_iterations: int = 5
    ) -> str:
        """
        带工具调用的流式LLM请求
        
        使用流式LLM调用，支持多段思考推送，工具调用前后推送思考事件。
        最大迭代次数为5次，防止无限循环。
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_iterations: 最大迭代次数
            
        Returns:
            最终响应文本
        """
        if not prompt or not prompt.strip():
            logger.warning(f"智能体 {self.name} 收到空的 prompt，使用默认提示")
            prompt = "请进行分析"
        
        if not system_prompt or not system_prompt.strip():
            system_prompt = self._get_default_system_prompt()
        
        tools = self.get_tools()
        
        # 构建初始消息列表
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt.strip()}
        ]
        
        final_content = ""
        
        for iteration in range(max_iterations):
            # 限流重试循环：对 RateLimitError 进行指数退避重试
            retry_count = 0
            max_retries = 3

            while True:
                # 每次（重试）尝试使用新的 thinking_id
                thinking_id = str(uuid.uuid4())

                await self.add_thinking(
                    f"正在调用大语言模型进行分析（第 {iteration + 1} 轮）"
                    + (f" - 第 {retry_count + 1} 次重试" if retry_count > 0 else ""),
                    thinking_id=thinking_id,
                    thinking_type="normal"
                )

                # 记录本轮开始前的状态，用于重试时回滚
                pre_retry_thinking_len = len(self.thinking_process)
                pre_retry_final_content = final_content

                try:
                    # 使用流式LLM调用，携带消息历史
                    async for event in self._llm_service.chat_stream_with_tools(
                        prompt="",  # 使用 messages 参数，此处为空
                        tools=tools,
                        messages=messages,
                        temperature=temperature
                    ):
                        # 处理开始思考
                        if event["type"] == "thinking_start":
                            pass  # 已在上方推送

                        # 处理普通内容片段
                        elif event["type"] == "content_chunk":
                            chunk_content = event["content"]
                            await self.add_streaming_thinking(
                                thinking_id=thinking_id,
                                chunk_content=chunk_content,
                                thinking_type="normal"
                            )
                            final_content += chunk_content

                        # 处理深度思考片段
                        elif event["type"] == "reasoning_chunk":
                            reasoning_content = event["content"]
                            await self.add_streaming_thinking(
                                thinking_id=thinking_id,
                                chunk_content=reasoning_content,
                                thinking_type="deep_thinking"
                            )

                        # 处理工具调用事件
                        elif event["type"] == "tool_calls":
                            tool_calls = event["tool_calls"]

                            # 添加 assistant 消息，携带工具调用信息
                            assistant_message = {
                                "role": "assistant",
                                "content": final_content if final_content else "正在调用工具...",
                                "tool_calls": [
                                    {
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tc["name"],
                                            "arguments": tc["arguments"]
                                        }
                                    }
                                    for tc in tool_calls
                                ]
                            }
                            messages.append(assistant_message)

                            # 执行所有工具调用
                            for tc in tool_calls:
                                tool_name = tc["name"]
                                tool_args = json.loads(tc["arguments"])
                                tool_chinese_name = get_tool_chinese_name(tool_name)

                                await self.add_thinking(f"正在{tool_chinese_name}...")

                                try:
                                    result = await asyncio.wait_for(
                                        self.execute_tool(tool_name, tool_args),
                                        timeout=30.0
                                    )
                                except asyncio.TimeoutError:
                                    tool_result = ToolResult.fail(f"工具 {tool_name} 执行超时（30秒）")
                                    await self.add_thinking(f"工具 {tool_name} 执行超时，已降级处理")
                                    result = tool_result

                                # 构建工具响应消息
                                tool_content = json.dumps(result.to_dict(), ensure_ascii=False, default=str)
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": tool_content if tool_content else "工具执行完成"
                                })

                            # 重置 final_content，用于收集下一轮工具执行后的结果
                            final_content = ""

                        # 处理完成事件
                        elif event["type"] == "complete":
                            final_content = event["content"]
                            # 标记流式思考完成
                            await self.add_streaming_thinking(
                                thinking_id, "",
                                "deep_thinking" if thinking_id in self._streaming_buffer and self._streaming_buffer[thinking_id] else "normal",
                                is_complete=True
                            )
                            # 添加 assistant 消息
                            if final_content:
                                messages.append({"role": "assistant", "content": final_content})
                            return final_content

                    # 正常完成流式迭代（没有 complete 事件但流结束），退出重试循环
                    break

                except RateLimitError as e:
                    # 仅对限流错误进行重试
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(
                            f"智能体 {self.name} LLM 请求已被限流 "
                            f"（已重试 {max_retries} 次），放弃重试"
                        )
                        friendly_msg = self._handle_llm_error(e)
                        self.error_message = friendly_msg
                        raise

                    # 回滚本轮已产生的部分 thinking_process 记录和流式缓冲区
                    while len(self.thinking_process) > pre_retry_thinking_len:
                        removed = self.thinking_process.pop()
                        self._streaming_buffer.pop(removed.get("thinking_id"), None)
                    final_content = pre_retry_final_content

                    # 指数退避 + 随机抖动
                    delay = min(2.0 * (2 ** (retry_count - 1)) + random.uniform(0, 1), 30)
                    await self.add_thinking(
                        f"LLM 请求被限流，{delay:.0f}秒后自动重试"
                        f"（第 {retry_count}/{max_retries} 次）..."
                    )
                    logger.warning(
                        f"智能体 {self.name} LLM 请求被限流，"
                        f"{delay:.1f}秒后重试（第 {retry_count}/{max_retries} 次）"
                    )
                    await asyncio.sleep(delay)
                    # 继续 while True 重试循环
                    continue

                except (PermissionDeniedError, APIError) as e:
                    # 非限流 API 错误直接抛出，不重试
                    friendly_msg = self._handle_llm_error(e)
                    self.error_message = friendly_msg
                    raise
                except Exception as e:
                    # 未知错误直接抛出
                    friendly_msg = self._handle_llm_error(e)
                    self.error_message = friendly_msg
                    raise

        # 达到最大迭代次数，返回最后一条消息内容
        return final_content
    
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
        
        tool_chinese_name = get_tool_chinese_name(tool_name)
        if result.success:
            await self.add_thinking(f"{tool_chinese_name}完成")
        else:
            await self.add_thinking(f"{tool_chinese_name}失败: {result.error}")
        
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
        context_str = json.dumps(context, ensure_ascii=False, indent=2, default=str)
        
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
            # 尝试从Markdown代码块中提取JSON
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)```', llm_response)
            if json_match:
                json_str = json_match.group(1).strip()
                result = json.loads(json_str)
                self.score = result.get("score")
                if self.score is not None:
                    try:
                        self.score = float(self.score)
                        self.score = max(0.0, min(10.0, self.score))
                    except (ValueError, TypeError):
                        self.score = None
                confidence_raw = result.get("confidence")
                if confidence_raw is not None:
                    try:
                        self.confidence = int(confidence_raw)
                        self.confidence = max(1, min(5, self.confidence))
                    except (ValueError, TypeError):
                        self.confidence = None
                ds_raw = result.get("data_sufficiency")
                if ds_raw in ("complete", "partial", "insufficient"):
                    self.data_sufficiency = ds_raw
                self.summary = result.get("summary")
                self.details = result.get("details", {})
                return result
            
            # 尝试提取第一个完整的JSON对象（通过括号匹配）
            json_start = llm_response.find("{")
            if json_start != -1:
                # 从第一个{开始，找到匹配的}
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(llm_response)):
                    if llm_response[i] == '{':
                        brace_count += 1
                    elif llm_response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    result = json.loads(json_str)
                    self.score = result.get("score")
                    if self.score is not None:
                        try:
                            self.score = float(self.score)
                            self.score = max(0.0, min(10.0, self.score))
                        except (ValueError, TypeError):
                            self.score = None
                    confidence_raw = result.get("confidence")
                    if confidence_raw is not None:
                        try:
                            self.confidence = int(confidence_raw)
                            self.confidence = max(1, min(5, self.confidence))
                        except (ValueError, TypeError):
                            self.confidence = None
                    ds_raw = result.get("data_sufficiency")
                    if ds_raw in ("complete", "partial", "insufficient"):
                        self.data_sufficiency = ds_raw
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
            use_rag: 是否使用RAG知识增强（若 embedding 未配置则自动禁用）
            use_tools: 是否使用工具调用
            
        Returns:
            分析结果字典
        """
        context["fund_code"] = fund_code

        # 注入当前日期信息到上下文，使智能体感知当前时间
        context["current_date"] = date.today().isoformat()
        context["current_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 检查 embedding 是否已配置，若未配置则自动禁用 RAG
        if use_rag:
            from app.core.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()
            if not settings_manager.is_embedding_configured():
                use_rag = False
                logger.info(f"智能体 {self.name}: Embedding 未配置，自动禁用 RAG")

        if use_rag:
            rag_context = await self.build_rag_context(
                query=f"{self.agent_type}分析 {fund_code}",
                context_type=self.agent_type
            )
            if rag_context:
                context["rag_knowledge"] = rag_context

        prompt = self.build_context_prompt(context)

        # 构建包含当前时间信息的系统提示词
        system_prompt = self.get_system_prompt()
        system_prompt += (
            f"\n\n## 当前时间信息\n"
            f"- 当前日期：{context['current_date']}\n"
            f"- 当前时间：{context['current_datetime']}\n\n"
            f"重要提示：请基于上述当前时间进行分析。数据中出现的日期如果早于或等于当前日期，"
            f"均为有效的历史数据。"
        )

        system_prompt += (
            "\n\n## 输出格式要求\n"
            "你必须输出合法的 JSON 格式，包含以下字段：\n"
            "- score: 评分（0-10的数字）\n"
            "- summary: 分析摘要（字符串）\n"
            "- details: 详细分析结果（对象）\n"
            "- confidence: 置信度（1-5的整数，1=低置信度，5=高置信度）\n"
            "- data_sufficiency: 数据充足度（'complete'/'partial'/'insufficient'）\n\n"
            "重要规则：\n"
            "1. 当数据不足时，必须在 data_sufficiency 中标注 'insufficient' 或 'partial'，并在 summary 中明确说明\n"
            "2. 不得在数据不足时编造分析结论，应明确声明无法分析\n"
            "3. confidence 应反映你对分析结果的确信程度，数据不足时 confidence 不得超过2"
        )

        llm_response = await self.call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
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
            "rag_context": self._rag_context,
            "confidence": self.confidence,
            "data_sufficiency": self.data_sufficiency,
            "data_sufficient": self.data_sufficient
        }
