"""
分析会话模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisSession(Base):
    """分析会话表"""
    __tablename__ = "analysis_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # 允许为空，支持匿名用户
    fund_code = Column(String(6), ForeignKey("funds.fund_code"), nullable=False, index=True)
    user_preference = Column(String(20), nullable=False, default="neutral")
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 关联关系
    user = relationship("User", back_populates="sessions")
    fund = relationship("Fund", back_populates="sessions")
    agent_outputs = relationship("AgentOutput", back_populates="session", cascade="all, delete-orphan")
    report = relationship("DecisionReport", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnalysisSession {self.id}>"


class AgentOutput(Base):
    """智能体输出表"""
    __tablename__ = "agent_outputs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("analysis_sessions.id"), nullable=False, index=True)
    agent_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    score = Column(Numeric(3, 1), nullable=True)
    summary = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    thinking_process = Column(Text, nullable=True)
    tools_called = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # 关联关系
    session = relationship("AnalysisSession", back_populates="agent_outputs")
    
    def __repr__(self):
        return f"<AgentOutput {self.agent_type}>"


class DecisionReport(Base):
    """决策报告表"""
    __tablename__ = "decision_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("analysis_sessions.id"), nullable=False, unique=True)
    short_term_decision = Column(JSONB, nullable=False)
    long_term_decision = Column(JSONB, nullable=False)
    cost_matrix = Column(JSONB, nullable=False)
    risk_alerts = Column(JSONB, nullable=False)
    agent_scores = Column(JSONB, nullable=False)
    trend_chart = Column(JSONB, nullable=True)
    disclaimer = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关联关系
    session = relationship("AnalysisSession", back_populates="report")
    
    def __repr__(self):
        return f"<DecisionReport {self.session_id}>"
