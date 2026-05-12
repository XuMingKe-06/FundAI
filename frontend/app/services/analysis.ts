import { get, post, type ApiResponse } from './api'

/**
 * 分析会话状态
 */
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed'

/**
 * 创建分析会话请求参数
 */
export interface CreateAnalysisRequest {
  fundCode: string
  userPreference?: string
  analysisDepth?: 'quick' | 'standard' | 'deep'
  previousSessionId?: string
}

/**
 * 分析会话信息
 */
export interface AnalysisSession {
  sessionId: string
  fundCode: string
  fundName: string
  status: AnalysisStatus
  progress: number
  createdAt: string
  updatedAt: string
  completedAt?: string
}

/**
 * 分析报告
 */
export interface AnalysisReport {
  sessionId: string
  fundCode: string
  fundName: string
  summary: AnalysisSummary
  multiAgentAnalysis: MultiAgentAnalysis
  investmentAdvice: InvestmentAdvice
  riskAssessment: RiskAssessment
  generatedAt: string
}

/**
 * 分析摘要
 */
export interface AnalysisSummary {
  overallRating: number
  recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell'
  keyFindings: string[]
  suitableFor: string[]
  notSuitableFor: string[]
}

/**
 * 多智能体分析结果
 */
export interface MultiAgentAnalysis {
  fundamentalAnalysis: AgentAnalysis
  technicalAnalysis: AgentAnalysis
  sentimentAnalysis: AgentAnalysis
  costAnalysis: AgentAnalysis
  consensus: ConsensusResult
}

/**
 * 单个智能体分析结果
 */
export interface AgentAnalysis {
  agentName: string
  score: number
  confidence: number
  findings: string[]
  signals: AnalysisSignal[]
  reasoning: string
}

/**
 * 分析信号
 */
export interface AnalysisSignal {
  type: 'bullish' | 'bearish' | 'neutral'
  strength: 'strong' | 'moderate' | 'weak'
  indicator: string
  value: string
  description: string
}

/**
 * 共识结果
 */
export interface ConsensusResult {
  overallScore: number
  agreement: number
  conflictPoints: string[]
  agreedPoints: string[]
}

/**
 * 投资建议
 */
export interface InvestmentAdvice {
  shortTerm: TermAdvice
  longTerm: TermAdvice
  positionSizing: PositionSizing
  entryStrategy: string
  exitStrategy: string
}

/**
 * 期限建议
 */
export interface TermAdvice {
  horizon: string
  action: 'buy' | 'sell' | 'hold'
  targetPrice?: number
  stopLoss?: number
  expectedReturn: number
  riskLevel: 'low' | 'medium' | 'high'
  confidence: number
  reasoning: string
}

/**
 * 仓位建议
 */
export interface PositionSizing {
  suggestedRatio: number
  maxRatio: number
  minRatio: number
  reasoning: string
}

/**
 * 风险评估
 */
export interface RiskAssessment {
  overallRisk: 'low' | 'medium' | 'high'
  riskScore: number
  riskFactors: RiskFactor[]
  mitigationStrategies: string[]
}

/**
 * 风险因素
 */
export interface RiskFactor {
  category: string
  factor: string
  severity: 'low' | 'medium' | 'high'
  probability: number
  impact: string
  description: string
}

/**
 * 创建分析会话
 * @param fundCode - 基金代码
 * @param userPreference - 用户偏好（可选）
 * @returns 分析会话信息
 */
export async function createAnalysisSession(
  fundCode: string,
  userPreference?: string
): Promise<ApiResponse<AnalysisSession>> {
  const requestData: CreateAnalysisRequest = {
    fundCode,
    userPreference,
  }
  return post<AnalysisSession>('/analysis/sessions', requestData)
}

/**
 * 获取分析报告
 * @param sessionId - 会话 ID
 * @returns 分析报告详情
 */
export async function getAnalysisReport(
  sessionId: string
): Promise<ApiResponse<AnalysisReport>> {
  return get<AnalysisReport>(`/analysis/sessions/${sessionId}/report`)
}

/**
 * 获取分析进度
 * @param sessionId - 会话 ID
 * @returns 分析进度信息
 */
export async function getAnalysisProgress(
  sessionId: string
): Promise<ApiResponse<AnalysisSession>> {
  return get<AnalysisSession>(`/analysis/sessions/${sessionId}/progress`)
}

/**
 * 取消分析
 * @param sessionId - 会话 ID
 * @returns 取消结果
 */
export async function cancelAnalysis(
  sessionId: string
): Promise<ApiResponse<null>> {
  return post<null>(`/analysis/sessions/${sessionId}/cancel`)
}

/**
 * 重新分析
 * @param sessionId - 会话 ID
 * @returns 新的分析会话信息
 */
export async function reanalyze(
  sessionId: string
): Promise<ApiResponse<AnalysisSession>> {
  return post<AnalysisSession>(`/analysis/sessions/${sessionId}/reanalyze`)
}

/**
 * 导出分析报告
 * @param sessionId - 会话 ID
 * @param format - 导出格式 (pdf/json/markdown)
 * @returns 导出文件 URL
 */
export async function exportReport(
  sessionId: string,
  format: 'pdf' | 'json' | 'markdown' = 'pdf'
): Promise<ApiResponse<{ url: string; expiresAt: string }>> {
  return get<{ url: string; expiresAt: string }>(
    `/analysis/sessions/${sessionId}/export`,
    { params: { format } }
  )
}

export const analysisService = {
  createAnalysisSession,
  getAnalysisReport,
  getAnalysisProgress,
  cancelAnalysis,
  reanalyze,
  exportReport,
}

export default analysisService
