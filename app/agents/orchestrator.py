"""
智能体编排器
实现智能体并行调度和 SSE 事件推送
"""
import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional, AsyncGenerator
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json

from app.agents.base import BaseAgent
from app.agents.fundamental import FundamentalAgent
from app.agents.technical import TechnicalAgent
from app.agents.risk import RiskAgent
from app.agents.cost import CostAgent
from app.agents.sentiment import SentimentAgent
from app.agents.decision import DecisionAgent
from app.data_sources.manager import datasource_manager

logger = logging.getLogger(__name__)


class EventType(Enum):
    """SSE 事件类型枚举"""
    AGENT_STATUS = "agent_status"
    THINKING = "thinking"
    LLM_THINKING_STREAM = "llm_thinking_stream"
    TOOL_CALL = "tool_call"
    AGENT_COMPLETE = "agent_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"


@dataclass
class SSEEvent:
    """SSE 事件数据结构"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
    
    def to_sse_message(self) -> str:
        """转换为 SSE 消息格式"""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.data, ensure_ascii=False, default=str)}\n\n"


class EventCallback:
    """
    SSE 事件回调处理器
    用于收集和推送智能体执行过程中的事件
    """
    
    def __init__(self):
        self._events: List[SSEEvent] = []
        self._queue: asyncio.Queue = asyncio.Queue()
    
    async def emit_agent_status(
        self, 
        agent_type: str, 
        status: str,
        agent_name: Optional[str] = None
    ) -> None:
        """
        发送智能体状态事件
        
        Args:
            agent_type: 智能体类型
            status: 状态（running/completed/failed）
            agent_name: 智能体名称
        """
        event = SSEEvent(
            event_type=EventType.AGENT_STATUS,
            data={
                "agent_type": agent_type,
                "agent_name": agent_name or agent_type,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
        logger.debug(f"智能体状态更新: {agent_type} -> {status}")
    
    async def emit_thinking(
        self, 
        agent_type: str, 
        content: str
    ) -> None:
        """
        发送思考过程事件
        
        Args:
            agent_type: 智能体类型
            content: 思考内容
        """
        event = SSEEvent(
            event_type=EventType.THINKING,
            data={
                "agent_type": agent_type,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
    
    async def emit_llm_thinking_stream(
        self,
        agent_type: str,
        thinking_id: str,
        content: str,
        thinking_type: str = "normal",
        is_complete: bool = False
    ) -> None:
        """
        发送LLM流式思考内容事件
        
        Args:
            agent_type: 智能体类型
            thinking_id: 思考段落唯一标识
            content: 思考内容片段
            thinking_type: 思考类型，normal（普通思考）或 deep_thinking（深度思考）
            is_complete: 是否完成
        """
        event = SSEEvent(
            event_type=EventType.LLM_THINKING_STREAM,
            data={
                "agent_type": agent_type,
                "thinking_id": thinking_id,
                "content": content,
                "thinking_type": thinking_type,
                "is_complete": is_complete,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
    
    async def emit_tool_call(
        self,
        agent_type: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        status: str = "pending"
    ) -> None:
        """
        发送工具调用事件
        
        Args:
            agent_type: 智能体类型
            tool_name: 工具名称
            tool_args: 工具参数
            result: 执行结果
            status: 调用状态（pending/success/failed）
        """
        event = SSEEvent(
            event_type=EventType.TOOL_CALL,
            data={
                "agent_type": agent_type,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "result": result,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
        logger.debug(f"工具调用事件: {agent_type} -> {tool_name} ({status})")
    
    async def emit_agent_complete(
        self, 
        agent_type: str,
        score: Optional[float],
        summary: Optional[str],
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送智能体完成事件
        
        Args:
            agent_type: 智能体类型
            score: 评分
            summary: 摘要
            details: 详细信息
        """
        event = SSEEvent(
            event_type=EventType.AGENT_COMPLETE,
            data={
                "agent_type": agent_type,
                "status": "completed",
                "score": score,
                "summary": summary,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
        logger.info(f"智能体完成: {agent_type}, 评分: {score}")
    
    async def emit_analysis_complete(
        self, 
        session_id: str,
        final_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送分析完成事件
        
        Args:
            session_id: 会话ID
            final_result: 最终结果
        """
        event = SSEEvent(
            event_type=EventType.ANALYSIS_COMPLETE,
            data={
                "session_id": session_id,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "result_summary": final_result
            }
        )
        await self._queue.put(event)
        self._events.append(event)
        logger.info(f"分析完成: session_id={session_id}")
    
    async def emit_error(
        self, 
        error_type: str,
        message: str,
        agent_type: Optional[str] = None
    ) -> None:
        """
        发送错误事件
        
        Args:
            error_type: 错误类型
            message: 错误消息
            agent_type: 相关智能体类型
        """
        event = SSEEvent(
            event_type=EventType.ERROR,
            data={
                "error_type": error_type,
                "message": message,
                "agent_type": agent_type,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        await self._queue.put(event)
        self._events.append(event)
        logger.error(f"错误事件: {error_type} - {message}")
    
    async def get_event(self) -> Optional[SSEEvent]:
        """获取下一个事件"""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    def get_all_events(self) -> List[SSEEvent]:
        """获取所有事件"""
        return self._events.copy()


class AgentOrchestrator:
    """
    智能体编排器
    
    负责协调多个智能体的并行执行和结果汇总，
    支持 SSE 事件推送和超时控制。
    """
    
    AGENT_TIMEOUT_SECONDS = 120
    
    ANALYSIS_AGENTS_CONFIG = [
        ("fundamental", "基本面分析师", FundamentalAgent),
        ("technical", "技术分析师", TechnicalAgent),
        ("risk", "风险分析师", RiskAgent),
        ("cost", "成本分析师", CostAgent),
        ("sentiment", "情绪分析师", SentimentAgent),
    ]
    
    def __init__(self):
        self.analysis_agents: List[BaseAgent] = []
        self.decision_agent: Optional[DecisionAgent] = None
        self.agent_results: Dict[str, Any] = {}
        self.fundamental_agent: Optional[BaseAgent] = None
        self.technical_agent: Optional[BaseAgent] = None
        self.risk_agent: Optional[BaseAgent] = None
        self.cost_agent: Optional[BaseAgent] = None
        self.sentiment_agent: Optional[BaseAgent] = None
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """初始化所有智能体实例"""
        for agent_type, agent_name, agent_class in self.ANALYSIS_AGENTS_CONFIG:
            agent = agent_class()
            self.analysis_agents.append(agent)
            if agent_type == "fundamental":
                self.fundamental_agent = agent
            elif agent_type == "technical":
                self.technical_agent = agent
            elif agent_type == "risk":
                self.risk_agent = agent
            elif agent_type == "cost":
                self.cost_agent = agent
            elif agent_type == "sentiment":
                self.sentiment_agent = agent
        
        self.decision_agent = DecisionAgent()
        logger.info(f"智能体初始化完成: {len(self.analysis_agents)} 个分析智能体, 1 个决策智能体")
    
    def _get_agent_by_type(self, agent_type: str) -> Optional[BaseAgent]:
        """根据类型获取智能体实例"""
        for agent in self.analysis_agents:
            if agent.agent_type == agent_type:
                return agent
        if self.decision_agent and self.decision_agent.agent_type == agent_type:
            return self.decision_agent
        return None
    
    async def _build_context(self, fund_code: str) -> Dict[str, Any]:
        """
        构建分析上下文
        
        从数据源管理器获取基金基础信息、净值历史等数据，
        为智能体分析提供必要的上下文信息。
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含基金信息的上下文字典
        """
        # 规范化基金代码：Tushare 需要带 .OF 后缀
        normalized_code = fund_code
        if '.' not in fund_code:
            normalized_code = f"{fund_code}.OF"
        
        logger.info(f"开始构建分析上下文，原始代码: {fund_code}, 规范化代码: {normalized_code}")
        
        context: Dict[str, Any] = {
            "fund_code": fund_code,
            "normalized_code": normalized_code,
            "build_time": datetime.now(timezone.utc).isoformat(),
            "data_source": {},
            "data_status": {}  # 记录各数据源的获取状态
        }
        
        # 获取基金基础信息
        try:
            fund_info = await datasource_manager.get_fund_info(normalized_code)
            if fund_info:
                context["fund_info"] = fund_info
                context["fund_name"] = fund_info.get("fund_name", "未知")
                context["fund_type"] = fund_info.get("fund_type", "未知")
                context["fund_scale"] = fund_info.get("scale") or fund_info.get("current_scale", 0)
                context["establish_date"] = fund_info.get("establish_date")
                context["fund_manager"] = fund_info.get("fund_manager", "未知")
                context["data_status"]["fund_info"] = "success"
                logger.info(f"获取基金信息成功: {normalized_code} - {context.get('fund_name')}")
            else:
                # 尝试使用原始代码
                fund_info = await datasource_manager.get_fund_info(fund_code)
                if fund_info:
                    context["fund_info"] = fund_info
                    context["fund_name"] = fund_info.get("fund_name", "未知")
                    context["fund_type"] = fund_info.get("fund_type", "未知")
                    context["fund_scale"] = fund_info.get("scale") or fund_info.get("current_scale", 0)
                    context["establish_date"] = fund_info.get("establish_date")
                    context["fund_manager"] = fund_info.get("fund_manager", "未知")
                    context["data_status"]["fund_info"] = "success"
                    logger.info(f"获取基金信息成功(原始代码): {fund_code} - {context.get('fund_name')}")
                else:
                    logger.warning(f"未找到基金信息: {fund_code}")
                    context["fund_info"] = {}
                    context["fund_name"] = "未知"
                    context["data_status"]["fund_info"] = "not_found"
        except Exception as e:
            logger.error(f"获取基金信息失败: {e}")
            context["fund_info"] = {}
            context["fund_name"] = "未知"
            context["data_status"]["fund_info"] = f"error: {str(e)}"
        
        # 获取净值历史数据
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            nav_history = await datasource_manager.get_nav_history(
                normalized_code, start_date, end_date
            )
            if nav_history and len(nav_history) > 0:
                context["nav_history"] = nav_history
                context["nav_count"] = len(nav_history)
                latest_nav = nav_history[-1] if nav_history else {}
                context["current_nav"] = latest_nav.get("nav")
                context["nav_date"] = latest_nav.get("trade_date") or latest_nav.get("date")
                context["data_status"]["nav_history"] = "success"
                logger.info(f"获取净值历史成功: {normalized_code}, 共 {len(nav_history)} 条记录")
            else:
                # 尝试使用原始代码
                nav_history = await datasource_manager.get_nav_history(
                    fund_code, start_date, end_date
                )
                if nav_history and len(nav_history) > 0:
                    context["nav_history"] = nav_history
                    context["nav_count"] = len(nav_history)
                    latest_nav = nav_history[-1] if nav_history else {}
                    context["current_nav"] = latest_nav.get("nav")
                    context["nav_date"] = latest_nav.get("trade_date") or latest_nav.get("date")
                    context["data_status"]["nav_history"] = "success"
                    logger.info(f"获取净值历史成功(原始代码): {fund_code}, 共 {len(nav_history)} 条记录")
                else:
                    context["nav_history"] = []
                    context["nav_count"] = 0
                    context["data_status"]["nav_history"] = "not_found"
                    logger.warning(f"未找到净值历史: {fund_code}")
        except Exception as e:
            logger.error(f"获取净值历史失败: {e}")
            context["nav_history"] = []
            context["nav_count"] = 0
            context["data_status"]["nav_history"] = f"error: {str(e)}"
        
        # 获取持仓信息
        try:
            holdings = await datasource_manager.get_holdings(normalized_code)
            if holdings:
                context["holdings"] = holdings
                context["data_status"]["holdings"] = "success"
                logger.info(f"获取持仓信息成功: {normalized_code}")
            else:
                holdings = await datasource_manager.get_holdings(fund_code)
                if holdings:
                    context["holdings"] = holdings
                    context["data_status"]["holdings"] = "success"
                    logger.info(f"获取持仓信息成功(原始代码): {fund_code}")
                else:
                    context["holdings"] = {}
                    context["data_status"]["holdings"] = "not_found"
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            context["holdings"] = {}
            context["data_status"]["holdings"] = f"error: {str(e)}"
        
        # 获取费率信息
        try:
            fees = await datasource_manager.get_fund_fees(normalized_code)
            if fees:
                context["fees"] = fees
                context["data_status"]["fees"] = "success"
                logger.info(f"获取费率信息成功: {normalized_code}")
            else:
                fees = await datasource_manager.get_fund_fees(fund_code)
                if fees:
                    context["fees"] = fees
                    context["data_status"]["fees"] = "success"
                    logger.info(f"获取费率信息成功(原始代码): {fund_code}")
                else:
                    context["fees"] = {}
                    context["data_status"]["fees"] = "not_found"
        except Exception as e:
            logger.error(f"获取费率信息失败: {e}")
            context["fees"] = {}
            context["data_status"]["fees"] = f"error: {str(e)}"
        
        # 获取基金经理信息
        try:
            manager_info = await datasource_manager.get_fund_manager(normalized_code)
            if manager_info:
                context["manager_info"] = manager_info
                context["data_status"]["manager_info"] = "success"
                logger.info(f"获取基金经理信息成功: {normalized_code}")
            else:
                manager_info = await datasource_manager.get_fund_manager(fund_code)
                if manager_info:
                    context["manager_info"] = manager_info
                    context["data_status"]["manager_info"] = "success"
                    logger.info(f"获取基金经理信息成功(原始代码): {fund_code}")
                else:
                    context["manager_info"] = {}
                    context["data_status"]["manager_info"] = "not_found"
        except Exception as e:
            logger.error(f"获取基金经理信息失败: {e}")
            context["manager_info"] = {}
            context["data_status"]["manager_info"] = f"error: {str(e)}"
        
        # 记录数据获取摘要
        data_summary = {k: v for k, v in context["data_status"].items()}
        logger.info(f"数据获取摘要: {data_summary}")
        
        return context
    
    async def _run_agent(
        self,
        agent: BaseAgent,
        fund_code: str,
        context: Dict[str, Any],
        event_callback: EventCallback
    ) -> Dict[str, Any]:
        """
        执行单个智能体分析
        
        包含超时控制和错误处理，智能体执行过程中的思考内容
        会通过事件回调实时推送。
        
        Args:
            agent: 智能体实例
            fund_code: 基金代码
            context: 分析上下文
            event_callback: 事件回调处理器
            
        Returns:
            智能体分析结果
        """
        agent_type = agent.agent_type
        agent_name = agent.name
        
        await event_callback.emit_agent_status(agent_type, "running", agent_name)
        
        async def thinking_callback(content: str) -> None:
            await event_callback.emit_thinking(agent_type, content)
        
        async def streaming_thinking_callback(thinking_id: str, chunk_content: str, thinking_type: str) -> None:
            await event_callback.emit_llm_thinking_stream(
                agent_type=agent_type,
                thinking_id=thinking_id,
                content=chunk_content,
                thinking_type=thinking_type
            )
        
        async def tool_call_callback(
            tool_name: str,
            tool_args: Dict[str, Any],
            result: Optional[Dict[str, Any]] = None,
            status: str = "pending"
        ) -> None:
            await event_callback.emit_tool_call(
                agent_type=agent_type,
                tool_name=tool_name,
                tool_args=tool_args,
                result=result,
                status=status
            )
        
        agent.set_thinking_callback(thinking_callback)
        
        if hasattr(agent, 'set_streaming_thinking_callback'):
            agent.set_streaming_thinking_callback(streaming_thinking_callback)
        
        if hasattr(agent, 'set_tool_call_callback'):
            agent.set_tool_call_callback(tool_call_callback)
        
        try:
            result = await asyncio.wait_for(
                agent.run(fund_code, context),
                timeout=self.AGENT_TIMEOUT_SECONDS
            )
            
            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=agent.score,
                summary=agent.summary,
                details=agent.details
            )
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"智能体 {agent_name} 执行超时（超过 {self.AGENT_TIMEOUT_SECONDS} 秒）"
            logger.error(error_msg)
            
            await event_callback.emit_error(
                error_type="TimeoutError",
                message=error_msg,
                agent_type=agent_type
            )
            
            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=None,
                summary=f"执行超时",
                details={"error": error_msg}
            )
            
            return {
                "agent_type": agent_type,
                "status": "timeout",
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"智能体 {agent_name} 执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            await event_callback.emit_error(
                error_type=type(e).__name__,
                message=error_msg,
                agent_type=agent_type
            )
            
            await event_callback.emit_agent_complete(
                agent_type=agent_type,
                score=None,
                summary=f"执行失败",
                details={"error": str(e)}
            )
            
            return {
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e)
            }
            
        finally:
            agent.set_thinking_callback(None)
            if hasattr(agent, 'set_tool_call_callback'):
                agent.set_tool_call_callback(None)
    
    async def run_analysis(
        self,
        session_id: str,
        fund_code: str,
        user_preference: str = "neutral",
        analysis_mode: str = "parallel"
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        执行完整分析流程

        实现两阶段执行：
        1. 第一阶段：并行或串行执行基本面、技术、风险、成本、情绪五个分析智能体
        2. 第二阶段：等待第一阶段全部完成后，执行决策智能体

        通过异步生成器实时推送 SSE 事件。

        Args:
            session_id: 会话ID
            fund_code: 基金代码
            user_preference: 用户风险偏好（conservative/neutral/aggressive）
            analysis_mode: 分析模式（parallel/sequential）

        Yields:
            SSEEvent: 实时事件流
        """
        event_callback = EventCallback()
        self.agent_results = {}

        async def event_producer():
            """事件生产协程"""
            while True:
                event = await event_callback.get_event()
                if event:
                    yield event

        producer_gen = event_producer()

        async def run_analysis_task():
            """分析任务协程"""
            try:
                context = await self._build_context(fund_code)
                context["user_preference"] = user_preference
                context["session_id"] = session_id
                context["analysis_mode"] = analysis_mode

                if analysis_mode == "sequential":
                    logger.info(f"开始串行执行分析智能体, session_id={session_id}")
                    for agent in self.analysis_agents:
                        logger.info(f"执行智能体: {agent.agent_type}, session_id={session_id}")
                        result = await self._run_agent(agent, fund_code, context, event_callback)
                        if isinstance(result, Exception):
                            logger.error(f"智能体 {agent.agent_type} 执行异常: {result}")
                            self.agent_results[agent.agent_type] = {
                                "agent_type": agent.agent_type,
                                "status": "failed",
                                "error": str(result)
                            }
                        else:
                            self.agent_results[agent.agent_type] = result
                        # 将当前结果注入 context 供后续 agent 参考
                        context["agent_results"] = self.agent_results
                else:
                    logger.info(f"开始并行执行分析智能体, session_id={session_id}")

                    analysis_tasks = [
                        self._run_agent(agent, fund_code, context, event_callback)
                        for agent in self.analysis_agents
                    ]

                    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        agent_type = self.analysis_agents[i].agent_type
                        if isinstance(result, Exception):
                            logger.error(f"智能体 {agent_type} 执行异常: {result}")
                            self.agent_results[agent_type] = {
                                "agent_type": agent_type,
                                "status": "failed",
                                "error": str(result)
                            }
                        else:
                            self.agent_results[agent_type] = result
                
                logger.info(f"所有分析智能体执行完成, session_id={session_id}")
                
                decision_context = context.copy()
                decision_context["agent_results"] = self.agent_results
                
                logger.info(f"开始执行决策智能体, session_id={session_id}")
                
                decision_result = await self._run_agent(
                    self.decision_agent,
                    fund_code,
                    decision_context,
                    event_callback
                )
                
                self.agent_results["decision"] = decision_result
                
                final_result = {
                    "session_id": session_id,
                    "fund_code": fund_code,
                    "user_preference": user_preference,
                    "agent_results": {
                        k: {
                            "score": v.get("score"),
                            "summary": v.get("summary"),
                            "status": v.get("status", "completed")
                        }
                        for k, v in self.agent_results.items()
                    },
                    "decision": decision_result.get("details", {}),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
                
                await event_callback.emit_analysis_complete(session_id, final_result)
                
            except Exception as e:
                logger.error(f"分析流程异常: {e}", exc_info=True)
                await event_callback.emit_error(
                    error_type="AnalysisError",
                    message=str(e)
                )
        
        analysis_task = asyncio.create_task(run_analysis_task())
        
        completed = False
        
        while not completed:
            if analysis_task.done():
                completed = True
            
            async for event in producer_gen:
                yield event
            
            if not completed:
                await asyncio.sleep(0.05)
        
        try:
            await analysis_task
        except Exception as e:
            logger.error(f"分析任务异常: {e}")
        
        remaining_events = event_callback.get_all_events()
        for event in remaining_events:
            if event not in [e async for e in producer_gen]:
                yield event
    
    async def run_analysis_agents(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        analysis_mode: str = "parallel"
    ) -> Dict[str, Any]:
        """
        运行分析智能体（兼容旧接口）

        Args:
            fund_code: 基金代码
            context: 分析上下文
            progress_callback: 进度回调函数
            analysis_mode: 分析模式（parallel/sequential）

        Returns:
            各智能体分析结果
        """
        event_callback = EventCallback()

        async def run_agent(agent: BaseAgent):
            """运行单个智能体"""
            try:
                if progress_callback:
                    await progress_callback(agent.agent_type, "running", None, None)

                result = await self._run_agent(agent, fund_code, context, event_callback)

                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "completed",
                        agent.score,
                        agent.summary
                    )

                return agent.agent_type, result
            except Exception as e:
                if progress_callback:
                    await progress_callback(
                        agent.agent_type,
                        "failed",
                        None,
                        str(e)
                    )
                return agent.agent_type, {"error": str(e)}

        if analysis_mode == "sequential":
            for agent in self.analysis_agents:
                agent_type, result = await run_agent(agent)
                self.agent_results[agent_type] = result
                # 将当前结果注入 context 供后续 agent 参考
                context["agent_results"] = self.agent_results
        else:
            tasks = [run_agent(agent) for agent in self.analysis_agents]
            results = await asyncio.gather(*tasks)

            for agent_type, result in results:
                self.agent_results[agent_type] = result

        return self.agent_results
    
    async def run_decision_agent(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        运行决策智能体（兼容旧接口）
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            progress_callback: 进度回调函数
            
        Returns:
            决策智能体分析结果
        """
        event_callback = EventCallback()
        
        try:
            if progress_callback:
                await progress_callback("decision", "running", None, None)
            
            context["agent_results"] = self.agent_results
            
            result = await self._run_agent(
                self.decision_agent, fund_code, context, event_callback
            )
            
            if progress_callback:
                await progress_callback(
                    "decision",
                    "completed",
                    None,
                    self.decision_agent.summary
                )
            
            return result
        except Exception as e:
            if progress_callback:
                await progress_callback("decision", "failed", None, str(e))
            return {"error": str(e)}
    
    async def run_full_analysis(
        self,
        fund_code: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        运行完整分析流程（兼容旧接口）
        
        Args:
            fund_code: 基金代码
            context: 分析上下文
            progress_callback: 进度回调函数
            
        Returns:
            完整分析结果
        """
        await self.run_analysis_agents(fund_code, context, progress_callback)
        
        decision_result = await self.run_decision_agent(fund_code, context, progress_callback)
        
        return {
            "analysis_agents": self.agent_results,
            "decision_agent": decision_result,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_agent_thinking_process(self, agent_type: str) -> List[Dict[str, str]]:
        """
        获取智能体思考过程
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            思考过程列表
        """
        if agent_type in self.agent_results:
            return self.agent_results[agent_type].get("thinking_process", [])
        if agent_type == "decision" and self.decision_agent:
            return self.decision_agent.thinking_process
        return []
    
    def get_agent_result(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定智能体的分析结果
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            智能体分析结果
        """
        return self.agent_results.get(agent_type)
    
    def get_all_results(self) -> Dict[str, Any]:
        """
        获取所有智能体的分析结果
        
        Returns:
            所有智能体结果字典
        """
        return self.agent_results.copy()
