"""
LLM 服务模块
提供统一的大模型调用接口，配置从前端设置页面管理
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from functools import lru_cache

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务类
    
    统一封装大模型调用，配置从 data/config.json 读取
    """
    
    _instance: Optional["LLMService"] = None
    _client: Optional[OpenAI] = None
    _async_client: Optional[AsyncOpenAI] = None
    
    def __new__(cls) -> "LLMService":
        """
        单例模式，确保全局只有一个实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化 LLM 服务
        延迟加载客户端，不在初始化时创建连接
        """
        self._model: Optional[str] = None
        self._api_key: Optional[str] = None
        self._base_url: Optional[str] = None
        self._initialized = False
    
    def _get_settings_manager(self):
        """获取配置管理器（延迟导入避免循环依赖）"""
        from app.core.settings_manager import get_settings_manager
        return get_settings_manager()
    
    def _initialize(self):
        """
        延迟初始化客户端
        每次调用时检测配置变更，自动重建客户端
        """
        sm = self._get_settings_manager()
        
        current_base_url = sm.get("llm.api_base_url", "")
        current_key = sm.get("llm.api_key", "")
        current_model = sm.get("llm.model", "")

        if self._initialized and self._model == current_model and self._api_key == current_key and self._base_url == current_base_url:
            return

        if self._initialized:
            logger.info(f"检测到 LLM 配置变更，重新初始化: model={self._model} -> {current_model}")

        self._model = current_model
        self._api_key = current_key
        self._base_url = current_base_url

        if not self._api_key:
            raise ValueError(
                "请在前端设置页面配置 LLM API Key"
            )
        
        if not self._base_url:
            raise ValueError(
                "请在前端设置页面配置 LLM API Base URL"
            )

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url
        )
        self._async_client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url
        )

        self._initialized = True
        logger.info(f"LLM 服务初始化完成: base_url={self._base_url}, model={self._model}")
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        单轮对话（同步）
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API
            
        Returns:
            模型回复文本
        """
        self._initialize()
        
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})
        
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def chat_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        单轮对话（异步）
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API
            
        Returns:
            模型回复文本
        """
        self._initialize()
        
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})
        
        response = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式对话（异步生成器）
        
        适用于 SSE 推送场景，逐 token 返回
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API
            
        Yields:
            模型回复的文本片段
        """
        self._initialize()
        
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})
        
        stream = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def chat_stream_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话 + 工具调用（异步生成器）

        支持流式输出与工具调用事件推送，工具由外部执行后再次调用此方法。

        Args:
            prompt: 用户输入（或携带工具结果的新一轮消息），当 messages 为空时使用
            tools: 工具定义列表，符合 OpenAI function calling 格式
            system_prompt: 系统提示词
            messages: 可选的消息历史列表，如果提供则覆盖 prompt 和 system_prompt
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API

        Yields:
            - {"type": "thinking_start"}  - 开始思考
            - {"type": "content_chunk", "content": "..."}  - 内容片段
            - {"type": "reasoning_chunk", "content": "..."}  - 深度思考片段（如果有）
            - {"type": "tool_calls", "tool_calls": [...]}  - 工具调用列表
            - {"type": "complete", "content": "..."}  - 完成事件
        """
        self._initialize()

        if messages:
            message_list = messages
        else:
            if not prompt or not prompt.strip():
                raise ValueError("prompt 参数不能为空")
            message_list: List[Dict[str, Any]] = []
            if system_prompt and system_prompt.strip():
                message_list.append({"role": "system", "content": system_prompt.strip()})
            message_list.append({"role": "user", "content": prompt.strip()})

        yield {"type": "thinking_start"}

        response = await self._async_client.chat.completions.create(
            model=self._model,
            messages=message_list,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            tools=tools,
            **kwargs
        )

        content_buffer: List[str] = []
        reasoning_buffer: List[str] = []
        tool_calls_map: Dict[int, Dict[str, Any]] = {}

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if reasoning:
                reasoning_buffer.append(reasoning)
                CHUNK_SIZE = 80
                if len(reasoning) > CHUNK_SIZE:
                    for i in range(0, len(reasoning), CHUNK_SIZE):
                        piece = reasoning[i:i + CHUNK_SIZE]
                        yield {"type": "reasoning_chunk", "content": piece}
                        if i + CHUNK_SIZE < len(reasoning):
                            await asyncio.sleep(0.02)
                else:
                    yield {"type": "reasoning_chunk", "content": reasoning}

            if delta.content:
                content_buffer.append(delta.content)
                CHUNK_SIZE = 80
                if len(delta.content) > CHUNK_SIZE:
                    for i in range(0, len(delta.content), CHUNK_SIZE):
                        piece = delta.content[i:i + CHUNK_SIZE]
                        yield {"type": "content_chunk", "content": piece}
                        if i + CHUNK_SIZE < len(delta.content):
                            await asyncio.sleep(0.02)
                else:
                    yield {"type": "content_chunk", "content": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = getattr(tc, "index", 0)
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name if tc.function else "",
                            "args_str": "",
                        }
                    if tc.function and tc.function.arguments:
                        tool_calls_map[idx]["args_str"] += tc.function.arguments

        if tool_calls_map:
            tool_calls_list = [
                {
                    "id": info["id"],
                    "name": info["name"],
                    "arguments": info["args_str"],
                }
                for _, info in sorted(tool_calls_map.items())
            ]
            yield {"type": "tool_calls", "tool_calls": tool_calls_list}
        else:
            final_content = "".join(content_buffer)
            yield {"type": "complete", "content": final_content}

    async def chat_with_history(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        多轮对话（带历史记录）
        
        Args:
            prompt: 当前用户输入
            history: 历史对话记录，格式为 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API
            
        Returns:
            模型回复文本
        """
        self._initialize()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        response = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def chat_with_history_stream(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        多轮对话流式输出（带历史记录）
        
        Args:
            prompt: 当前用户输入
            history: 历史对话记录
            system_prompt: 系统提示词
            temperature: 温度参数（0-2）
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数传递给 API
            
        Yields:
            模型回复的文本片段
        """
        self._initialize()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        stream = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].content
    
    def get_client(self) -> OpenAI:
        """
        获取底层 OpenAI 客户端
        
        供高级用法，如直接调用 API
        
        Returns:
            OpenAI 客户端实例
        """
        self._initialize()
        return self._client
    
    def get_async_client(self) -> AsyncOpenAI:
        """
        获取底层异步 OpenAI 客户端
        
        Returns:
            AsyncOpenAI 客户端实例
        """
        self._initialize()
        return self._async_client
    
    def get_model_name(self) -> str:
        """
        获取当前使用的模型名称
        
        Returns:
            模型名称字符串
        """
        self._initialize()
        return self._model
    
    def get_base_url(self) -> str:
        """
        获取当前使用的 API Base URL
        
        Returns:
            API Base URL 字符串
        """
        self._initialize()
        return self._base_url
    
    def get_embedding_config(self) -> Dict[str, str]:
        """
        获取 Embedding 配置
        
        Returns:
            包含 api_base_url, api_key, model 的字典
        """
        sm = self._get_settings_manager()
        return {
            "api_base_url": sm.get("llm.embedding_api_base_url", ""),
            "api_key": sm.get("llm.embedding_api_key", ""),
            "model": sm.get("llm.embedding_model", ""),
        }


@lru_cache()
def get_llm_service() -> LLMService:
    """
    获取 LLM 服务单例
    
    Returns:
        LLMService 实例
    """
    return LLMService()
