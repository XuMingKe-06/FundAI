"""
分析会话模型
适配 SQLite：使用 String(36) 替代 UUID，JSON 替代 JSONB
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Numeric, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisSession(Base):
    """分析会话表"""
    __tablename__ = "analysis_sessions"

    # 主键，使用 String(36) 存储 UUID 字符串
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 基金代码，外键关联基金表
    fund_code = Column(String(6), ForeignKey("funds.fund_code"), nullable=False, index=True)
    # 用户偏好：保守/中性/激进
    user_preference = Column(String(20), nullable=False, default="neutral")
    # 分析模式：并行/串行
    analysis_mode = Column(String(20), nullable=False, default="parallel")
    # 上一次分析会话 ID，用于连续分析
    previous_session_id = Column(
        String(36), ForeignKey("analysis_sessions.id"), nullable=True, index=True
    )
    # 会话状态：pending / running / completed / failed
    status = Column(String(20), nullable=False, default="pending")
    # 创建时间
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # 完成时间
    completed_at = Column(DateTime, nullable=True)

    # 关联关系
    fund = relationship("Fund", back_populates="sessions")
    agent_outputs = relationship("AgentOutput", back_populates="session", cascade="all, delete-orphan")
    report = relationship("DecisionReport", back_populates="session", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnalysisSession {self.id}>"


class AgentOutput(Base):
    """智能体输出表"""
    __tablename__ = "agent_outputs"

    # 主键，使用 String(36) 存储 UUID 字符串
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 所属分析会话 ID
    session_id = Column(String(36), ForeignKey("analysis_sessions.id"), nullable=False, index=True)
    # 智能体类型：fundamental / technical / risk / cost / sentiment
    agent_type = Column(String(20), nullable=False)
    # 智能体执行状态
    status = Column(String(20), nullable=False)
    # 评分（0.0 - 10.0）
    score = Column(Numeric(3, 1), nullable=True)
    # 分析摘要
    summary = Column(Text, nullable=True)
    # 详细分析结果（JSON 格式）
    details = Column(JSON, nullable=True)
    # 思考过程
    thinking_process = Column(Text, nullable=True)
    # 调用的工具列表（JSON 格式）
    tools_called = Column(JSON, nullable=True)
    # 错误信息
    error_message = Column(Text, nullable=True)
    # 开始执行时间
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # 执行完成时间
    completed_at = Column(DateTime, nullable=True)
    # 执行耗时（毫秒）
    duration_ms = Column(Integer, nullable=True)

    # 关联关系
    session = relationship("AnalysisSession", back_populates="agent_outputs")

    def __repr__(self):
        return f"<AgentOutput {self.agent_type}>"


class DecisionReport(Base):
    """决策报告表"""
    __tablename__ = "decision_reports"

    # 主键，使用 String(36) 存储 UUID 字符串
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 所属分析会话 ID（唯一，一个会话对应一份报告）
    session_id = Column(String(36), ForeignKey("analysis_sessions.id"), nullable=False, unique=True)
    # 短线决策建议（7-30天）
    short_term_decision = Column(JSON, nullable=False)
    # 长线决策建议（6个月+）
    long_term_decision = Column(JSON, nullable=False)
    # 成本矩阵
    cost_matrix = Column(JSON, nullable=False)
    # 风险提示
    risk_alerts = Column(JSON, nullable=False)
    # 各智能体评分汇总
    agent_scores = Column(JSON, nullable=False)
    # 趋势图数据
    trend_chart = Column(JSON, nullable=True)
    # 免责声明
    disclaimer = Column(Text, nullable=False)
    # 报告生成时间
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # 关联关系
    session = relationship("AnalysisSession", back_populates="report")

    def __repr__(self):
        return f"<DecisionReport {self.session_id}>"
