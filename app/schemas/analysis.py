"""
分析会话相关Schema
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    """创建分析会话请求"""
    fund_code: str = Field(..., description="基金代码", min_length=6, max_length=6)
    user_preference: str = Field(default="neutral", description="风险偏好")
    previous_session_id: Optional[str] = Field(
        default=None, description="上一轮分析会话ID，用于重新分析时参考历史报告"
    )
    analysis_mode: str = Field(default="parallel", description="分析模式: parallel 或 sequential")


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(..., description="会话ID")
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    user_preference: str = Field(..., description="风险偏好")
    analysis_mode: str = Field(..., description="分析模式")
    status: str = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    @model_validator(mode='after')
    def ensure_timezone_aware(self):
        for field_name in ['created_at', 'completed_at']:
            value = getattr(self, field_name, None)
            if value is not None and value.tzinfo is None:
                setattr(self, field_name, value.replace(tzinfo=timezone.utc))
        return self
    
    class Config:
        from_attributes = True


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    session_id: str = Field(..., description="会话ID")
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    user_preference: str = Field(..., description="风险偏好")
    analysis_mode: str = Field(..., description="分析模式")
    status: str = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")

    @model_validator(mode='after')
    def ensure_timezone_aware(self):
        if self.created_at is not None and self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        return self


class AgentStatusEvent(BaseModel):
    """智能体状态事件"""
    agent_type: str = Field(..., description="智能体类型")
    status: str = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")


class ThinkingEvent(BaseModel):
    """思考过程事件"""
    agent_type: str = Field(..., description="智能体类型")
    content: str = Field(..., description="思考内容")
    timestamp: str = Field(..., description="时间戳")


class ToolCallEvent(BaseModel):
    """工具调用事件"""
    agent_type: str = Field(..., description="智能体类型")
    tool: str = Field(..., description="工具名称")
    args: Dict[str, Any] = Field(..., description="工具参数")
    timestamp: str = Field(..., description="时间戳")


class AgentCompleteEvent(BaseModel):
    """智能体完成事件"""
    agent_type: str = Field(..., description="智能体类型")
    status: str = Field(..., description="状态")
    score: Optional[float] = Field(default=None, description="评分")
    summary: Optional[str] = Field(default=None, description="摘要")
    timestamp: str = Field(..., description="时间戳")


class AnalysisCompleteEvent(BaseModel):
    """分析完成事件"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")


class ShortTermDecision(BaseModel):
    """短线决策"""
    direction: str = Field(..., description="操作方向")
    holding_period: str = Field(..., description="建议持有期")
    confidence: float = Field(..., description="置信度")
    reasons: List[str] = Field(..., description="核心依据")
    stop_profit: str = Field(..., description="止盈参考")
    stop_loss: str = Field(..., description="止损参考")


class LongTermDecision(BaseModel):
    """长线决策"""
    direction: str = Field(..., description="操作方向")
    confidence: float = Field(..., description="置信度")
    reasons: List[str] = Field(..., description="核心依据")
    dip_investment_suggestion: Optional[str] = Field(default=None, description="定投建议")


class CostMatrixItem(BaseModel):
    """成本矩阵项"""
    holding_period: str = Field(..., description="持有期")
    purchase_fee: str = Field(..., description="申购费率")
    redemption_fee: str = Field(..., description="赎回费率")
    total_fee: str = Field(..., description="总费率")
    breakeven: str = Field(..., description="盈亏平衡点")


class TrendDataPoint(BaseModel):
    """走势数据点"""
    date: str = Field(..., description="日期")
    value: float = Field(..., description="净值")
    upper_bound: Optional[float] = Field(default=None, description="上界")
    lower_bound: Optional[float] = Field(default=None, description="下界")


class TrendChart(BaseModel):
    """走势图数据"""
    historical_data: List[TrendDataPoint] = Field(..., description="历史走势数据")
    prediction_data: List[TrendDataPoint] = Field(..., description="预测走势数据")
    chart_config: Dict[str, str] = Field(..., description="图表配置")


class AgentScores(BaseModel):
    """智能体评分"""
    fundamental: float = Field(..., description="基本面评分")
    technical: float = Field(..., description="技术面评分")
    risk: float = Field(..., description="风险评分")
    cost: float = Field(..., description="成本评分")
    sentiment: float = Field(..., description="情绪评分")


class AnalysisReport(BaseModel):
    """分析报告"""
    session_id: str = Field(..., description="会话ID")
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: datetime = Field(..., description="完成时间")
    short_term_decision: ShortTermDecision = Field(..., description="短线决策")
    long_term_decision: LongTermDecision = Field(..., description="长线决策")
    cost_matrix: List[CostMatrixItem] = Field(..., description="成本矩阵")
    risk_alerts: List[str] = Field(..., description="风险提示")
    agent_scores: AgentScores = Field(..., description="智能体评分")
    trend_chart: Optional[TrendChart] = Field(default=None, description="走势图数据")
    disclaimer: str = Field(..., description="免责声明")

    @model_validator(mode='after')
    def ensure_timezone_aware(self):
        for field_name in ['created_at', 'completed_at']:
            value = getattr(self, field_name, None)
            if value is not None and value.tzinfo is None:
                setattr(self, field_name, value.replace(tzinfo=timezone.utc))
        return self


class SessionListItem(BaseModel):
    """会话列表项"""
    session_id: str = Field(..., description="会话ID")
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    status: str = Field(..., description="会话状态")
    short_term_direction: Optional[str] = Field(default=None, description="短线方向")
    long_term_direction: Optional[str] = Field(default=None, description="长线方向")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    @model_validator(mode='after')
    def ensure_timezone_aware(self):
        for field_name in ['created_at', 'completed_at']:
            value = getattr(self, field_name, None)
            if value is not None and value.tzinfo is None:
                setattr(self, field_name, value.replace(tzinfo=timezone.utc))
        return self
    
    class Config:
        from_attributes = True


class AgentOutputInfo(BaseModel):
    """智能体输出信息"""
    agent_type: str = Field(..., description="智能体类型")
    status: str = Field(..., description="执行状态")
    score: Optional[float] = Field(default=None, description="评分")
    summary: Optional[str] = Field(default=None, description="摘要")
    thinking_process: Optional[List[Dict[str, str]]] = Field(default=None, description="思考过程")
    tools_called: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具调用记录")
    duration_ms: Optional[int] = Field(default=None, description="执行时长")


class SessionDetail(BaseModel):
    """会话详情"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    fund_code: str = Field(..., description="基金代码")
    fund_name: str = Field(..., description="基金名称")
    user_preference: str = Field(..., description="风险偏好")
    status: str = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    agent_outputs: List[AgentOutputInfo] = Field(..., description="智能体输出列表")

    @model_validator(mode='after')
    def ensure_timezone_aware(self):
        for field_name in ['created_at', 'completed_at']:
            value = getattr(self, field_name, None)
            if value is not None and value.tzinfo is None:
                setattr(self, field_name, value.replace(tzinfo=timezone.utc))
        return self
