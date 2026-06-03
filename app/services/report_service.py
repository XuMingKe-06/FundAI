"""
报告保存服务
处理智能体输出快照、决策报告和降级报告的持久化
"""
import json
from loguru import logger
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.analysis import AgentOutput, DecisionReport
from app.agents.orchestrator import AgentOrchestrator

async def save_agent_snapshot(session_id: str, agent) -> None:
    """使用独立 DB 会话保存单个智能体输出快照（支持页面刷新恢复）"""
    try:
        async with AsyncSessionLocal() as db_session:
            # 先清理该智能体的旧输出
            await db_session.execute(
                delete(AgentOutput).where(
                    AgentOutput.session_id == session_id,
                    AgentOutput.agent_type == agent.agent_type
                )
            )
            tools_called_data = None
            if agent.tools_called:
                tools_called_data = json.loads(json.dumps(agent.tools_called, ensure_ascii=False, default=str))
            agent_output = AgentOutput(
                session_id=session_id,
                agent_type=agent.agent_type,
                status=agent.status,
                score=agent.score,
                summary=agent.summary,
                details=agent.details,
                thinking_process=json.dumps(agent.thinking_process, ensure_ascii=False, default=str) if agent.thinking_process else None,
                tools_called=tools_called_data,
                error_message=agent.error_message,
                started_at=agent.started_at or datetime.now(timezone.utc),
                completed_at=agent.completed_at or datetime.now(timezone.utc),
                duration_ms=agent.duration_ms
            )
            db_session.add(agent_output)
            await db_session.commit()
    except Exception as e:
        logger.warning(f"保存智能体 {agent.agent_type} 快照失败: {e}")

async def save_agent_outputs(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator
):
    """保存智能体输出到数据库"""
    try:
        # 先清理该会话的旧输出（防止新旧编排器重叠导致重复数据）
        await db_session.execute(
            delete(AgentOutput).where(AgentOutput.session_id == session_id)
        )

        # 保存分析智能体输出
        for agent in orchestrator.analysis_agents:
            # 序列化 tools_called，确保 date 对象被转换
            tools_called_data = None
            if agent.tools_called:
                tools_called_data = json.loads(json.dumps(agent.tools_called, ensure_ascii=False, default=str))

            agent_output = AgentOutput(
                session_id=session_id,
                agent_type=agent.agent_type,
                status=agent.status,
                score=agent.score,
                summary=agent.summary,
                details=agent.details,
                thinking_process=json.dumps(agent.thinking_process, ensure_ascii=False, default=str) if agent.thinking_process else None,
                tools_called=tools_called_data,
                error_message=agent.error_message,
                started_at=agent.started_at or datetime.now(timezone.utc),
                completed_at=agent.completed_at,
                duration_ms=agent.duration_ms
            )
            db_session.add(agent_output)

        # 保存决策智能体输出
        decision_agent = orchestrator.decision_agent
        # 序列化 tools_called，确保 date 对象被转换
        decision_tools_called_data = None
        if decision_agent.tools_called:
            decision_tools_called_data = json.loads(json.dumps(decision_agent.tools_called, ensure_ascii=False, default=str))

        decision_output = AgentOutput(
            session_id=session_id,
            agent_type=decision_agent.agent_type,
            status=decision_agent.status,
            score=decision_agent.score,
            summary=decision_agent.summary,
            details=decision_agent.details,
            thinking_process=json.dumps(decision_agent.thinking_process, ensure_ascii=False, default=str) if decision_agent.thinking_process else None,
            tools_called=decision_tools_called_data,
            error_message=decision_agent.error_message,
            started_at=decision_agent.started_at or datetime.now(timezone.utc),
            completed_at=decision_agent.completed_at,
            duration_ms=decision_agent.duration_ms
        )
        db_session.add(decision_output)

        await db_session.commit()
        logger.info(f"会话 {session_id} 的智能体输出已保存")

    except Exception as e:
        logger.error(f"保存智能体输出失败: {e}")
        await db_session.rollback()
        raise

def _build_fallback_short_term(orchestrator: AgentOrchestrator) -> dict:
    """从各分析智能体构建降级短线决策数据"""
    reasons = []
    direction = "hold"

    for agent in orchestrator.analysis_agents:
        if agent.summary:
            reasons.append(f"{agent.name}：{agent.summary}")

    # 根据评分趋势判断方向
    tech_agent = next((a for a in orchestrator.analysis_agents if a.agent_type == "technical"), None)
    if tech_agent and tech_agent.score is not None:
        if tech_agent.score >= 4.0:
            direction = "buy"
        elif tech_agent.score <= 2.0:
            direction = "sell"

    if not reasons:
        reasons.append("决策智能体执行失败，基于各分析智能体摘要生成")

    return {
        "direction": direction,
        "holding_period": "7-15天",
        "confidence": 0.3,
        "reasons": reasons[:5],
        "stop_profit": "建议根据个人风险偏好设置",
        "stop_loss": "建议设置5%-8%止损线"
    }

def _build_fallback_long_term(orchestrator: AgentOrchestrator) -> dict:
    """从各分析智能体构建降级长线决策数据"""
    reasons = []
    direction = "hold"

    for agent in orchestrator.analysis_agents:
        if agent.summary:
            reasons.append(f"{agent.name}：{agent.summary}")

    # 根据基本面评分判断方向
    fund_agent = next((a for a in orchestrator.analysis_agents if a.agent_type == "fundamental"), None)
    if fund_agent and fund_agent.score is not None:
        if fund_agent.score >= 4.0:
            direction = "buy"
        elif fund_agent.score <= 2.0:
            direction = "sell"

    if not reasons:
        reasons.append("决策智能体执行失败，基于各分析智能体摘要生成")

    return {
        "direction": direction,
        "confidence": 0.3,
        "reasons": reasons[:5],
        "dip_investment_suggestion": "建议等待决策分析完成后再做定投决策"
    }

async def save_decision_report(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator
):
    """保存决策报告到数据库"""
    try:
        decision_agent = orchestrator.decision_agent
        details = decision_agent.details or {}

        # 从决策智能体详情中提取决策数据
        short_term_decision = details.get("short_term_decision", {})
        long_term_decision = details.get("long_term_decision", {})

        # 如果决策智能体失败，从各分析智能体构建降级决策数据
        if decision_agent.status == "failed" or not short_term_decision:
            short_term_decision = _build_fallback_short_term(orchestrator)
        if decision_agent.status == "failed" or not long_term_decision:
            long_term_decision = _build_fallback_long_term(orchestrator)

        # 从各分析智能体直接提取评分（而非依赖决策智能体 details 中的 agent_scores）
        agent_scores = {}
        for agent in orchestrator.analysis_agents:
            if agent.score is not None:
                agent_scores[agent.agent_type] = float(agent.score)
        # 补全缺失的评分字段
        default_scores = {"fundamental": 0.0, "technical": 0.0, "risk": 0.0, "cost": 0.0, "sentiment": 0.0}
        default_scores.update(agent_scores)
        agent_scores = default_scores

        # 从成本智能体获取成本矩阵
        cost_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "cost":
                cost_agent = agent
                break

        cost_matrix = []
        if cost_agent and cost_agent.details:
            cost_matrix_raw = cost_agent.details.get("cost_matrix", [])
            for item in cost_matrix_raw:
                # 成本智能体 _build_cost_matrix 使用 holding_period 和 holding_days 字段
                holding_period = item.get("holding_period", "") or item.get("label", "")
                purchase_fee = item.get("purchase_fee", 0)
                redemption_fee = item.get("redemption_fee", 0)
                total_fee = item.get("total_fee", 0)
                cost_matrix.append({
                    "holding_period": holding_period,
                    "purchase_fee": f"{purchase_fee * 100:.2f}%" if isinstance(purchase_fee, (int, float)) else str(purchase_fee),
                    "redemption_fee": f"{redemption_fee * 100:.2f}%" if isinstance(redemption_fee, (int, float)) else str(redemption_fee),
                    "total_fee": f"{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(total_fee),
                    "breakeven": f"约{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(item.get("breakeven", ""))
                })

        # 从风险智能体获取风险提示
        risk_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "risk":
                risk_agent = agent
                break

        risk_alerts = []
        if risk_agent and risk_agent.details:
            risk_alerts = risk_agent.details.get("risk_alerts", [])
        # 如果风险智能体 details 中没有 risk_alerts，生成默认提示
        if not risk_alerts:
            risk_alerts = [
                "持仓数据可能存在滞后",
                "市场波动风险需关注",
                "投资需谨慎"
            ]

        # 从技术智能体和编排器上下文构建趋势图数据
        trend_chart = None
        technical_agent = None
        for agent in orchestrator.analysis_agents:
            if agent.agent_type == "technical":
                technical_agent = agent
                break

        # 尝试从技术智能体的工具调用结果中获取净值历史
        historical_data = []
        if technical_agent and technical_agent.tools_called:
            for tool_call in technical_agent.tools_called:
                if tool_call.get("name") == "get_nav_history":
                    result = tool_call.get("result", {})
                    if result and result.get("success"):
                        nav_data = result.get("data")
                        # data 字段直接就是净值列表
                        nav_list = nav_data if isinstance(nav_data, list) else nav_data.get("nav_history", []) if isinstance(nav_data, dict) else []
                        for item in nav_list:
                            date_val = item.get("date", "") or item.get("trade_date", "")
                            nav_val = item.get("nav") or item.get("unit_nav")
                            if date_val and nav_val is not None:
                                historical_data.append({
                                    "date": str(date_val)[:10],
                                    "value": float(nav_val)
                                })
                    break

        # 如果 tools_called 中没有净值数据，尝试从技术智能体实例属性获取
        if not historical_data and technical_agent and hasattr(technical_agent, '_full_nav_history'):
            nav_history = technical_agent._full_nav_history
            if nav_history:
                for item in nav_history:
                    # trade_date 可能是 date 对象或字符串
                    raw_date = item.get("date") or item.get("trade_date")
                    date_val = raw_date.isoformat() if hasattr(raw_date, 'isoformat') else str(raw_date) if raw_date else ""
                    nav_val = item.get("nav") or item.get("unit_nav")
                    if date_val and nav_val is not None:
                        historical_data.append({
                            "date": date_val[:10],
                            "value": float(nav_val)
                        })

        # 如果技术智能体没有净值数据，尝试从编排器上下文获取
        if not historical_data and hasattr(orchestrator, '_last_context'):
            nav_history = orchestrator._last_context.get("nav_history", [])
            for item in nav_history:
                raw_date = item.get("date") or item.get("trade_date")
                date_val = raw_date.isoformat() if hasattr(raw_date, 'isoformat') else str(raw_date) if raw_date else ""
                nav_val = item.get("nav") or item.get("unit_nav")
                if date_val and nav_val is not None:
                    historical_data.append({
                        "date": date_val[:10],
                        "value": float(nav_val)
                    })

        if historical_data:
            # 基于历史数据生成简单预测（最近5个数据点的趋势延伸）
            prediction_data = []
            if len(historical_data) >= 5:
                last_5 = historical_data[-5:]
                avg_change = 0
                for i in range(1, len(last_5)):
                    avg_change += last_5[i]["value"] - last_5[i-1]["value"]
                avg_change /= (len(last_5) - 1)

                last_val = historical_data[-1]["value"]
                last_date_str = historical_data[-1]["date"]
                try:
                    base_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
                except (ValueError, IndexError):
                    base_date = datetime.now(timezone.utc)

                for i in range(1, 6):
                    pred_date = (base_date + timedelta(days=i * 7)).strftime("%Y-%m-%d")
                    pred_val = last_val + avg_change * i
                    prediction_data.append({
                        "date": pred_date,
                        "value": round(pred_val, 4),
                        "upper_bound": round(pred_val * 1.02, 4),
                        "lower_bound": round(pred_val * 0.98, 4)
                    })

            trend_chart = {
                "historical_data": historical_data,
                "prediction_data": prediction_data,
                "chart_config": {
                    "historical_color": "#3B82F6",
                    "prediction_color": "#F97316",
                    "historical_label": "历史走势",
                    "prediction_label": "预测走势"
                }
            }

        # 先清理该会话的旧报告（防止新旧编排器重叠导致唯一约束冲突）
        await db_session.execute(
            delete(DecisionReport).where(DecisionReport.session_id == session_id)
        )

        # 创建决策报告
        report = DecisionReport(
            session_id=session_id,
            short_term_decision=short_term_decision,
            long_term_decision=long_term_decision,
            cost_matrix=cost_matrix,
            risk_alerts=risk_alerts,
            agent_scores=agent_scores,
            trend_chart=trend_chart,
            disclaimer="本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。"
        )

        db_session.add(report)
        await db_session.commit()
        logger.info(f"会话 {session_id} 的决策报告已保存")

    except Exception as e:
        logger.error(f"保存决策报告失败: {e}")
        await db_session.rollback()
        raise

async def save_fallback_report(
    db_session: AsyncSession,
    session_id: str,
    orchestrator: AgentOrchestrator,
    error_msg: str = ""
):
    """保存降级报告（当正常报告生成失败时）"""
    decision_agent = orchestrator.decision_agent
    details = decision_agent.details if decision_agent else {}

    # 从各智能体获取可用评分数据
    agent_scores = {}
    for agent in orchestrator.analysis_agents:
        if agent.score is not None:
            agent_scores[agent.agent_type] = float(agent.score)

    # 补全缺失的评分字段
    default_scores = {"fundamental": 0.0, "technical": 0.0, "risk": 0.0, "cost": 0.0, "sentiment": 0.0}
    default_scores.update(agent_scores)

    # 从决策智能体获取可用的决策数据
    short_term = details.get("short_term_decision", {})
    long_term = details.get("long_term_decision", {})

    # 构建降级短线决策：优先使用决策智能体数据，否则从各分析智能体构建
    if short_term and short_term.get("direction"):
        fallback_short_term = {
            "direction": short_term.get("direction", "hold"),
            "holding_period": short_term.get("holding_period", "7-15天"),
            "confidence": short_term.get("confidence", 0.3),
            "reasons": short_term.get("reasons", ["数据获取不完整，基于有限数据生成"]),
            "stop_profit": short_term.get("stop_profit", "建议根据个人风险偏好设置"),
            "stop_loss": short_term.get("stop_loss", "建议设置5%-8%止损线")
        }
    else:
        fallback_short_term = _build_fallback_short_term(orchestrator)

    # 构建降级长线决策：优先使用决策智能体数据，否则从各分析智能体构建
    if long_term and long_term.get("direction"):
        fallback_long_term = {
            "direction": long_term.get("direction", "hold"),
            "confidence": long_term.get("confidence", 0.3),
            "reasons": long_term.get("reasons", ["数据获取不完整，基于有限数据生成"]),
            "dip_investment_suggestion": long_term.get("dip_investment_suggestion", "建议等待数据完整后再做决策")
        }
    else:
        fallback_long_term = _build_fallback_long_term(orchestrator)

    # 从成本智能体获取成本矩阵
    cost_matrix = []
    for agent in orchestrator.analysis_agents:
        if agent.agent_type == "cost" and agent.details:
            cost_matrix_raw = agent.details.get("cost_matrix", [])
            for item in cost_matrix_raw:
                holding_period = item.get("holding_period", "") or item.get("label", "")
                purchase_fee = item.get("purchase_fee", 0)
                redemption_fee = item.get("redemption_fee", 0)
                total_fee = item.get("total_fee", 0)
                cost_matrix.append({
                    "holding_period": holding_period,
                    "purchase_fee": f"{purchase_fee * 100:.2f}%" if isinstance(purchase_fee, (int, float)) else str(purchase_fee),
                    "redemption_fee": f"{redemption_fee * 100:.2f}%" if isinstance(redemption_fee, (int, float)) else str(redemption_fee),
                    "total_fee": f"{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(total_fee),
                    "breakeven": f"约{total_fee * 100:.2f}%" if isinstance(total_fee, (int, float)) else str(item.get("breakeven", ""))
                })
            break

    # 从风险智能体获取风险提示
    risk_alerts = ["分析过程中部分数据获取失败，结果仅供参考", "投资需谨慎"]
    for agent in orchestrator.analysis_agents:
        if agent.agent_type == "risk" and agent.details:
            risk_alerts = agent.details.get("risk_alerts", risk_alerts)
            break

    disclaimer_text = "本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。"
    if error_msg:
        disclaimer_text = f"本报告由AI智能体自动生成。分析过程中出现错误：{error_msg}。基于有限数据生成，不构成任何投资建议。市场有风险，投资需谨慎。"

    report = DecisionReport(
        session_id=session_id,
        short_term_decision=fallback_short_term,
        long_term_decision=fallback_long_term,
        cost_matrix=cost_matrix,
        risk_alerts=risk_alerts,
        agent_scores=default_scores,
        trend_chart=None,
        disclaimer=disclaimer_text
    )

    db_session.add(report)
    await db_session.commit()
    logger.info(f"会话 {session_id} 的降级决策报告已保存")
