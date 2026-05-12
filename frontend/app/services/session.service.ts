import { get, post, del } from './api'
import type { PaginatedResponse } from './api'

/* 会话信息类型 */
export interface Session {
  id: string
  fundCode: string
  fundName: string
  status: string
  decision: string
  shortTermDecision?: string
  longTermDecision?: string
  createdAt: string
  updatedAt: string
  agentOutputs?: AgentOutputItem[]
}

/* 智能体输出项 */
export interface AgentOutputItem {
  agentType: string
  status: string
  score?: number | null
  summary?: string | null
  thinkingProcess?: Array<{ time: string; text: string }> | null
  toolsCalled?: Array<{
    name: string
    args: Record<string, any>
    result?: {
      success: boolean
      data?: any
      error?: string
    } | null
    time?: string
    timestamp?: string
  }> | null
  durationMs?: number | null
}

/* 后端返回的会话数据类型 */
interface SessionResponse {
  sessionId: string
  fundCode: string
  fundName: string
  status: string
  shortTermDirection?: string
  longTermDirection?: string
  createdAt: string
  completedAt?: string
}

/* 后端返回的会话详情数据类型 */
interface SessionDetailResponse {
  sessionId: string
  userId: string
  fundCode: string
  fundName: string
  userPreference: string
  status: string
  createdAt: string
  completedAt?: string
  agentOutputs: Array<{
    agentType: string
    status: string
    score?: number | null
    summary?: string | null
    thinkingProcess?: Array<{ time: string; text: string }> | null
    toolsCalled?: Array<{
      name: string
      args: Record<string, any>
      result?: { success: boolean; data?: any; error?: string } | null
      timestamp?: string
    }> | null
    durationMs?: number | null
  }>
}

/* 会话列表查询参数 */
export interface SessionListParams {
  page?: number
  size?: number
  keyword?: string
}

/* 创建会话参数 */
export interface CreateSessionParams {
  fundCode: string
  riskPreference?: 'conservative' | 'neutral' | 'aggressive'
}

/* 将后端响应映射为前端 Session 类型 */
function mapSessionResponse(response: SessionResponse): Session {
  return {
    id: response.sessionId,
    fundCode: response.fundCode,
    fundName: response.fundName,
    status: response.status,
    decision: response.shortTermDirection || response.longTermDirection || '待分析',
    shortTermDecision: response.shortTermDirection,
    longTermDecision: response.longTermDirection,
    createdAt: response.createdAt,
    updatedAt: response.completedAt || response.createdAt,
  }
}

/* 会话服务 */
export const sessionService = {
  /* 获取会话列表 */
  async getSessions(params: SessionListParams = {}): Promise<PaginatedResponse<Session>> {
    const response = await get<{ items: SessionResponse[]; total: number; page: number; size: number }>('/sessions', {
      page: params.page || 1,
      size: params.size || 20,
      keyword: params.keyword,
    })
    return {
      items: response.items.map(mapSessionResponse),
      total: response.total,
      page: response.page,
      pageSize: response.size,
    }
  },

  /* 获取单个会话详情 */
  async getSession(sessionId: string): Promise<Session> {
    const response = await get<SessionDetailResponse>(`/sessions/${sessionId}`)
    return {
      id: response.sessionId,
      fundCode: response.fundCode,
      fundName: response.fundName,
      status: response.status,
      decision: '待分析',
      createdAt: response.createdAt,
      updatedAt: response.completedAt || response.createdAt,
      agentOutputs: response.agentOutputs?.map(ao => ({
        agentType: ao.agentType,
        status: ao.status,
        score: ao.score,
        summary: ao.summary,
        thinkingProcess: ao.thinkingProcess,
        toolsCalled: ao.toolsCalled,
        durationMs: ao.durationMs,
      })) || [],
    }
  },

  /* 创建新会话 */
  async createSession(params: CreateSessionParams): Promise<Session> {
    const response = await post<SessionResponse>('/sessions', params)
    return mapSessionResponse(response)
  },

  /* 删除会话 */
  async deleteSession(sessionId: string): Promise<void> {
    await del(`/sessions/${sessionId}`)
  },

  /* 清空所有会话 */
  async clearSessions(): Promise<void> {
    await del('/sessions')
  },
}

export default sessionService
