"""
分析会话API端点
"""
import json
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_async_session
from app.core.redis_client import get_redis, CacheKeys, CacheExpire
from app.core.security import get_current_user
from app.models.user import User
from app.models.fund import Fund
from app.models.analysis import AnalysisSession, AgentOutput, DecisionReport
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.analysis import (
    CreateSessionRequest,
    CreateSessionResponse,
    AnalysisReport,
    SessionListItem,
    SessionDetail,
    AgentOutputInfo,
    ShortTermDecision,
    LongTermDecision,
    CostMatrixItem,
    AgentScores,
    TrendChart,
    TrendDataPoint
)

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/sessions", response_model=ApiResponse[CreateSessionResponse])
async def create_analysis_session(
    request: CreateSessionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """创建分析会话"""
    # 查询基金信息
    result = await session.execute(
        select(Fund).where(Fund.fund_code == request.fund_code)
    )
    fund = result.scalar_one_or_none()
    
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="基金不存在"
        )
    
    # 创建分析会话
    new_session = AnalysisSession(
        user_id=current_user.id,
        fund_code=request.fund_code,
        user_preference=request.user_preference,
        status="pending"
    )
    
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    
    return ApiResponse(
        code=200,
        message="分析会话创建成功",
        data=CreateSessionResponse(
            session_id=str(new_session.id),
            fund_code=new_session.fund_code,
            fund_name=fund.fund_name,
            user_preference=new_session.user_preference,
            status=new_session.status,
            created_at=new_session.created_at
        )
    )


@router.get("/sessions/{session_id}/stream")
async def stream_analysis(
    session_id: str,
    analysis_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """启动分析并通过SSE流式输出"""
    # 查询会话
    result = await analysis_session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session_obj = result.scalar_one_or_none()
    
    if not analysis_session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 查询基金信息
    fund_result = await analysis_session.execute(
        select(Fund).where(Fund.fund_code == analysis_session_obj.fund_code)
    )
    fund = fund_result.scalar_one_or_none()
    
    # 更新会话状态
    analysis_session_obj.status = "running"
    await analysis_session.commit()
    
    async def event_generator():
        """SSE事件生成器"""
        try:
            # 定义智能体列表
            agents = [
                ("fundamental", "基本面分析师"),
                ("technical", "技术分析师"),
                ("risk", "风险分析师"),
                ("cost", "成本分析师"),
                ("sentiment", "情绪分析师"),
                ("decision", "决策智能体")
            ]
            
            agent_outputs = {}
            
            # 模拟智能体分析过程
            for agent_type, agent_name in agents:
                # 发送智能体开始状态
                yield f"event: agent_status\ndata: {json.dumps({'agent_type': agent_type, 'status': 'running', 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                
                # 模拟思考过程
                thinking_steps = get_agent_thinking_steps(agent_type, fund)
                for step in thinking_steps:
                    yield f"event: thinking\ndata: {json.dumps({'agent_type': agent_type, 'content': step, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                    await asyncio.sleep(0.3)
                
                # 模拟分析完成
                agent_result = get_agent_result(agent_type, fund)
                agent_outputs[agent_type] = agent_result
                
                yield f"event: agent_complete\ndata: {json.dumps({'agent_type': agent_type, 'status': 'completed', 'score': agent_result.get('score'), 'summary': agent_result.get('summary'), 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
                
                await asyncio.sleep(0.5)
            
            # 更新会话状态
            analysis_session_obj.status = "completed"
            analysis_session_obj.completed_at = datetime.utcnow()
            await analysis_session.commit()
            
            # 发送分析完成事件
            yield f"event: analysis_complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed', 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
            
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error_type': 'AnalysisError', 'message': str(e), 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def get_agent_thinking_steps(agent_type: str, fund) -> list:
    """获取智能体思考步骤"""
    steps = {
        "fundamental": [
            "正在获取基金基础信息...",
            f"获取到基金概况：{fund.fund_name}，成立日期{fund.establish_date}，当前规模{fund.current_scale}亿...",
            "正在分析持仓结构...",
            "前十大重仓股占比58.3%，行业分布以消费、科技为主，集中度评价：中...",
            "正在分析基金经理履历...",
            "基金经理从业经验丰富，管理本基金时间较长，任期回报优秀...",
            "正在计算业绩基准比较...",
            "近1年超额收益率8.5%，信息比率0.72，表现良好...",
            "综合评估：基本面评分4.2分。基金经理经验丰富，持仓结构合理，业绩表现良好。"
        ],
        "technical": [
            "正在获取基金净值历史数据...",
            "获取到近3年净值数据，共732个交易日...",
            "正在计算均线系统...",
            "MA20=1.258, MA60=1.245, MA120=1.230，均线呈多头排列...",
            "正在计算MACD指标...",
            "MACD金叉，柱状图加速向上...",
            "正在计算RSI指标...",
            "RSI(14)=58.5，处于中性偏强区间...",
            "正在计算估值分位数...",
            "当前估值处于近3年45%分位，属于合理区间...",
            "综合评估：技术面评分3.8分。趋势向上，RSI中性偏强，估值合理。"
        ],
        "risk": [
            "正在计算波动风险...",
            "近1年年化波动率18.5%，相对同类平均处于中等水平...",
            "正在计算下行风险...",
            "近1年最大回撤12.3%，发生在2025年10月...",
            "正在计算夏普比率...",
            "夏普比率0.85，评价良好...",
            "正在计算Beta系数...",
            "Beta=0.92，波动略小于市场...",
            "正在分析持仓集中度风险...",
            "前十大占比58.3%，单一行业占比28%，集中度风险中等...",
            "综合评估：风险等级中等。波动率适中，需关注集中度风险。"
        ],
        "cost": [
            "正在获取基金费率信息...",
            "申购费率原价1.5%，代销平台折扣后0.15%...",
            "正在分析赎回费率阶梯...",
            "不满7天：1.50%，7-30天：0.75%，30天-1年：0.50%，1-2年：0.25%，2年以上：0%...",
            "正在计算成本矩阵...",
            "持有7天总费率1.65%，持有15天总费率0.90%，持有30天总费率0.65%...",
            "正在评估短线可行性...",
            "预期毛收益率4.2%，扣除15天持有成本后净收益率3.3%，具备成本可行性...",
            "综合评估：短线操作具备成本可行性，推荐持有期15天。"
        ],
        "sentiment": [
            "正在获取新闻舆情数据...",
            "近3日相关新闻12条，正面8条，负面2条，中性2条...",
            "正在分析相关板块资金流向...",
            "近5日相关ETF累计净流入3.2亿，近20日净流入8.5亿...",
            "正在分析社交媒体热度...",
            "讨论热度为历史均值的1.3倍，处于中等偏高水平...",
            "正在汇总机构观点...",
            "近1个月券商研报：买入5篇，增持3篇，中性2篇...",
            "综合评估：情绪评分+2。近期舆情偏正面，资金持续流入相关ETF。"
        ],
        "decision": [
            "正在汇总各分析智能体结果...",
            "基本面评分4.2，技术面评分3.8，风险等级中，成本可行，情绪+2...",
            "正在计算短线综合得分...",
            "短线得分 = 3.8*0.4 + 3.0*0.3 + 3.5*0.2 + 4.0*0.1 = 3.62...",
            "正在计算长线综合得分...",
            "长线得分 = 4.2*0.5 + 3.8*0.3 + 3.5*0.2 = 3.94...",
            "正在生成短线建议...",
            "短线建议：买入，建议持有期15天，置信度75%...",
            "正在生成长线建议...",
            "长线建议：买入，可考虑分批定投，置信度82%...",
            "综合决策完成：双轨决策建议已生成。"
        ]
    }
    return steps.get(agent_type, [])


def get_agent_result(agent_type: str, fund) -> dict:
    """获取智能体分析结果"""
    results = {
        "fundamental": {"score": 4.2, "summary": "基金经理经验丰富，持仓结构合理"},
        "technical": {"score": 3.8, "summary": "趋势向上，RSI中性偏强"},
        "risk": {"score": 3.5, "summary": "波动率适中，需关注集中度风险"},
        "cost": {"score": 4.0, "summary": "短线操作成本可接受"},
        "sentiment": {"score": 3.0, "summary": "市场情绪偏正面"},
        "decision": {"score": None, "summary": "综合研判完成，生成双轨决策"}
    }
    return results.get(agent_type, {})


@router.get("/sessions/{session_id}/report", response_model=ApiResponse[AnalysisReport])
async def get_analysis_report(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取分析报告"""
    # 查询会话
    result = await session.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    analysis_session = result.scalar_one_or_none()
    
    if not analysis_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 查询基金信息
    fund_result = await session.execute(
        select(Fund).where(Fund.fund_code == analysis_session.fund_code)
    )
    fund = fund_result.scalar_one_or_none()
    
    # 构建模拟报告
    report = AnalysisReport(
        session_id=str(analysis_session.id),
        fund_code=analysis_session.fund_code,
        fund_name=fund.fund_name if fund else "未知基金",
        created_at=analysis_session.created_at,
        completed_at=analysis_session.completed_at or datetime.utcnow(),
        short_term_decision=ShortTermDecision(
            direction="buy",
            holding_period="15天",
            confidence=0.75,
            reasons=[
                "技术面趋势向上，RSI处于中性区间",
                "成本效益较好，总费率0.90%",
                "市场情绪偏正面"
            ],
            stop_profit="预期收益率3.5%",
            stop_loss="最大回撤5%"
        ),
        long_term_decision=LongTermDecision(
            direction="buy",
            confidence=0.82,
            reasons=[
                "基本面评分4.2分，基金经理经验丰富",
                "估值处于历史低位，安全边际较高",
                "持仓结构合理，行业分散"
            ],
            dip_investment_suggestion="可考虑分批定投"
        ),
        cost_matrix=[
            CostMatrixItem(holding_period="7天", purchase_fee="0.15%", redemption_fee="1.50%", total_fee="1.65%", breakeven="约1.68%"),
            CostMatrixItem(holding_period="15天", purchase_fee="0.15%", redemption_fee="0.75%", total_fee="0.90%", breakeven="约0.91%"),
            CostMatrixItem(holding_period="30天", purchase_fee="0.15%", redemption_fee="0.50%", total_fee="0.65%", breakeven="约0.66%"),
            CostMatrixItem(holding_period="180天", purchase_fee="0.15%", redemption_fee="0.25%", total_fee="0.40%", breakeven="约0.40%"),
            CostMatrixItem(holding_period="1年", purchase_fee="0.15%", redemption_fee="0.00%", total_fee="0.15%", breakeven="约0.15%")
        ],
        risk_alerts=[
            "持仓数据截止2026-03-31，可能存在滞后",
            "基金规模较大，需关注调仓灵活性",
            "当前估值处于历史中位数，需关注市场波动",
            "场外基金净值每日更新一次，无法实时交易"
        ],
        agent_scores=AgentScores(
            fundamental=4.2,
            technical=3.8,
            risk=3.5,
            cost=4.0,
            sentiment=3.0
        ),
        trend_chart=TrendChart(
            historical_data=[
                TrendDataPoint(date="2026-01-14", value=1.2345),
                TrendDataPoint(date="2026-02-14", value=1.2567),
                TrendDataPoint(date="2026-03-14", value=1.2789),
                TrendDataPoint(date="2026-04-14", value=1.2850)
            ],
            prediction_data=[
                TrendDataPoint(date="2026-04-17", value=1.2850, upper_bound=1.2950, lower_bound=1.2750),
                TrendDataPoint(date="2026-04-24", value=1.2920, upper_bound=1.3120, lower_bound=1.2720),
                TrendDataPoint(date="2026-05-14", value=1.3100, upper_bound=1.3500, lower_bound=1.2700)
            ],
            chart_config={
                "historical_color": "#3B82F6",
                "prediction_color": "#F97316",
                "historical_label": "历史走势",
                "prediction_label": "预测走势"
            }
        ),
        disclaimer="本报告由AI智能体自动生成，基于公开数据及算法分析，不构成任何投资建议。市场有风险，投资需谨慎。"
    )
    
    return ApiResponse(code=200, message="success", data=report)
