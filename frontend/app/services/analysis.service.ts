import { get, post } from './api'

/* 分析报告类型 */
export interface AnalysisReport {
  sessionId: string
  fundCode: string
  fundName: string
  updatedAt: string

  /* 决策概览 */
  decision: {
    shortTerm: {
      direction: 'buy' | 'sell' | 'hold'
      holdingPeriod: number | string
      confidence: number
    }
    longTerm: {
      direction: 'buy' | 'sell' | 'hold'
      confidence: number
      dipSuggestion?: string
    }
  }

  /* 净值走势数据 */
  trendData: {
    historical: Array<{ date: string; value: number }>
    prediction: Array<{ date: string; value: number; upper: number; lower: number }>
  }

  /* 智能体评分 */
  scores: {
    fundamental: number
    technical: number
    risk: number
    cost: number
    sentiment: number
    overall: number
  }

  /* 成本矩阵 */
  costMatrix: Array<{
    holdingPeriod: string
    purchaseFee: string
    redemptionFee: string
    totalFee: string
    breakEvenPoint: string
    recommended?: boolean
  }>

  /* 短线详细建议 */
  shortTermDetail: {
    direction: string
    holdingPeriod: number | string
    reasons: string[]
    stopProfit: string
    stopLoss: string
  }

  /* 长线详细建议 */
  longTermDetail: {
    direction: string
    reasons: string[]
    dipSuggestion?: string
  }

  /* 风险提示 */
  riskAlerts: string[]
}

/* 后端 API 返回的原始报告数据结构（经过 transformKeys 转换为 camelCase 后） */
interface ApiReportResponse {
  sessionId: string
  fundCode: string
  fundName: string
  createdAt: string
  completedAt: string
  shortTermDecision: {
    direction: string
    holdingPeriod: string | number
    confidence: number
    reasons: string[]
    stopProfit: string
    stopLoss: string
  }
  longTermDecision: {
    direction: string
    confidence: number
    reasons: string[]
    dipInvestmentSuggestion?: string
  }
  costMatrix: Array<{
    holdingPeriod: string
    purchaseFee: string
    redemptionFee: string
    totalFee: string
    breakeven: string
  }>
  riskAlerts: string[]
  agentScores: {
    fundamental: number
    technical: number
    risk: number
    cost: number
    sentiment: number
  }
  trendChart?: {
    historicalData: Array<{ date: string; value: number }>
    predictionData: Array<{ date: string; value: number; upperBound?: number; lowerBound?: number }>
    chartConfig: Record<string, string>
  }
  disclaimer?: string
}

/* 将后端 API 响应映射为前端 AnalysisReport 接口 */
function mapApiReportToReport(apiReport: ApiReportResponse): AnalysisReport {
  const shortTerm = apiReport.shortTermDecision || {}
  const longTerm = apiReport.longTermDecision || {}
  const scores = apiReport.agentScores || {}
  const trendChart = apiReport.trendChart

  // 计算综合评分
  const scoreValues = [scores.fundamental, scores.technical, scores.risk, scores.cost, scores.sentiment].filter(v => v != null)
  const overall = scoreValues.length > 0 ? Math.round(scoreValues.reduce((a, b) => a + b, 0) / scoreValues.length * 10) / 10 : 3.0

  return {
    sessionId: apiReport.sessionId,
    fundCode: apiReport.fundCode,
    fundName: apiReport.fundName,
    updatedAt: apiReport.completedAt || apiReport.createdAt,

    decision: {
      shortTerm: {
        direction: (shortTerm.direction || 'hold') as 'buy' | 'sell' | 'hold',
        holdingPeriod: shortTerm.holdingPeriod ?? 0,
        confidence: shortTerm.confidence ?? 0.5,
      },
      longTerm: {
        direction: (longTerm.direction || 'hold') as 'buy' | 'sell' | 'hold',
        confidence: longTerm.confidence ?? 0.5,
        dipSuggestion: longTerm.dipInvestmentSuggestion,
      },
    },

    trendData: {
      historical: trendChart?.historicalData?.map(d => ({
        date: d.date,
        value: d.value,
      })) || [],
      prediction: trendChart?.predictionData?.map(d => ({
        date: d.date,
        value: d.value,
        upper: d.upperBound ?? d.value,
        lower: d.lowerBound ?? d.value,
      })) || [],
    },

    scores: {
      fundamental: scores.fundamental ?? 3.0,
      technical: scores.technical ?? 3.0,
      risk: scores.risk ?? 3.0,
      cost: scores.cost ?? 3.0,
      sentiment: scores.sentiment ?? 0.0,
      overall,
    },

    costMatrix: (apiReport.costMatrix || []).map(item => ({
      holdingPeriod: item.holdingPeriod || '',
      purchaseFee: item.purchaseFee || '',
      redemptionFee: item.redemptionFee || '',
      totalFee: item.totalFee || '',
      breakEvenPoint: item.breakeven || '',
    })),

    shortTermDetail: {
      direction: shortTerm.direction || 'hold',
      holdingPeriod: shortTerm.holdingPeriod ?? 0,
      reasons: shortTerm.reasons || [],
      stopProfit: shortTerm.stopProfit || '',
      stopLoss: shortTerm.stopLoss || '',
    },

    longTermDetail: {
      direction: longTerm.direction || 'hold',
      reasons: longTerm.reasons || [],
      dipSuggestion: longTerm.dipInvestmentSuggestion,
    },

    riskAlerts: apiReport.riskAlerts || [],
  }
}

/* 创建分析请求参数 */
export interface CreateAnalysisParams {
  fundCode: string
  riskPreference?: 'conservative' | 'neutral' | 'aggressive'
  previousSessionId?: string
  analysisMode?: 'parallel' | 'sequential'
}

/* 分析服务 */
export const analysisService = {
  /* 创建分析任务 */
  async createAnalysis(params: CreateAnalysisParams): Promise<{ sessionId: string; fundName?: string }> {
    /* 转换参数为后端期望的格式 */
    const response = await post<{ sessionId: string; fundName?: string }>('/analysis/sessions', {
      fund_code: params.fundCode,
      user_preference: params.riskPreference,
      previous_session_id: params.previousSessionId,
      analysis_mode: params.analysisMode || 'parallel',
    })
    return response
  },

  /* 获取分析报告 */
  async getReport(sessionId: string): Promise<AnalysisReport> {
    const apiReport = await get<ApiReportResponse>(`/analysis/sessions/${sessionId}/report`)
    return mapApiReportToReport(apiReport)
  },

  /* 获取分析任务实时状态（用于页面刷新/重连后恢复进度） */
  async getAnalysisStatus(sessionId: string): Promise<{
    sessionId: string
    fundCode: string
    status: string
    progress: number
    completedAgents: string[]
    runningAgents: string[]
    errorMessage: string | null
  }> {
    const response = await get<{
      session_id: string
      fund_code: string
      status: string
      progress: number
      completed_agents: string[]
      running_agents: string[]
      error_message: string | null
    }>(`/analysis/sessions/${sessionId}/status`)
    return {
      sessionId: response.session_id,
      fundCode: response.fund_code,
      status: response.status,
      progress: response.progress,
      completedAgents: response.completed_agents || [],
      runningAgents: response.running_agents || [],
      errorMessage: response.error_message,
    }
  },

  /* 获取 SSE 流式分析进度 */
  getAnalysisStream(sessionId: string): EventSource | null {
    if (!import.meta.client) return null

    const baseUrl = '/api/v1'
    const eventSource = new EventSource(`${baseUrl}/analysis/${sessionId}/stream`, {
      withCredentials: true,
    })

    return eventSource
  },

  /* 搜索基金 */
  async searchFunds(keyword: string): Promise<Array<{ code: string; name: string }>> {
    const response = await get<Array<{ code: string; name: string }>>('/funds/search', {
      keyword,
    })
    return response
  },
}

export default analysisService
