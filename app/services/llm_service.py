"""
LLM 服务模块
提供统一的大模型调用接口，支持阿里云百炼和 DeepSeek 切换
"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from functools import lru_cache
import logging

from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务类
    
    统一封装大模型调用，基于阿里云百炼 API
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
        self._provider = settings.LLM_PROVIDER
        self._model: Optional[str] = None
        self._api_key: Optional[str] = None
        self._base_url: Optional[str] = None
        self._initialized = False
    
    def _initialize(self):
        """
        延迟初始化客户端
        只在第一次调用时创建连接
        """
        if self._initialized:
            return
        
        self._initialize_aliyun()
        
        self._initialized = True
        logger.info(f"LLM 服务初始化完成: provider={self._provider}, model={self._model}")
    
    def _initialize_aliyun(self):
        """
        初始化阿里云百炼客户端
        
        API Key 读取优先级：
        1. 系统环境变量 DASHSCOPE_API_KEY
        2. 配置文件中的 ALIYUN_LLM_API_KEY
        """
        self._api_key = os.getenv("DASHSCOPE_API_KEY") or settings.ALIYUN_LLM_API_KEY
        if not self._api_key:
            raise ValueError(
                "请配置阿里云百炼 API Key：设置系统环境变量 DASHSCOPE_API_KEY "
                "或在 .env 文件中配置 ALIYUN_LLM_API_KEY"
            )
        
        self._base_url = settings.ALIYUN_LLM_API_BASE
        self._model = settings.ALIYUN_LLM_MODEL
        
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url
        )
        self._async_client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url
        )
    
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
        
        # 验证 prompt 不为空，阿里云 API 要求 content 字段必须有值
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        # 只有当 system_prompt 非空时才添加 system 消息
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
        
        # 验证 prompt 不为空，阿里云 API 要求 content 字段必须有值
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        # 只有当 system_prompt 非空时才添加 system 消息
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
        
        # 验证 prompt 不为空，阿里云 API 要求 content 字段必须有值
        if not prompt or not prompt.strip():
            raise ValueError("prompt 参数不能为空")
        
        messages = []
        # 只有当 system_prompt 非空时才添加 system 消息
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
                yield chunk.choices[0].delta.content
    
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
    
    def get_provider(self) -> str:
        """
        获取当前服务提供商
        
        Returns:
            服务提供商名称（aliyun）
        """
        return self._provider


@lru_cache()
def get_llm_service() -> LLMService:
    """
    获取 LLM 服务单例
    
    Returns:
        LLMService 实例
    """
    return LLMService()
