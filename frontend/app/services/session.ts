import { del, get, type ApiResponse, type PageResponse } from './api'
import type { AnalysisStatus } from './analysis'

/**
 * 会话列表项
 */
export interface SessionListItem {
  sessionId: string
  fundCode: string
  fundName: string
  status: AnalysisStatus
  overallRating?: number
  recommendation?: string
  createdAt: string
  updatedAt: string
}

/**
 * 会话详情
 */
export interface SessionDetail {
  sessionId: string
  fundCode: string
  fundName: string
  status: AnalysisStatus
  progress: number
  userPreference?: string
  createdAt: string
  updatedAt: string
  completedAt?: string
  fundInfo: SessionFundInfo
  summary?: SessionSummary
  messages: SessionMessage[]
}

/**
 * 会话中的基金信息
 */
export interface SessionFundInfo {
  fundCode: string
  fundName: string
  fundType: string
  fundManager: string
  currentNav: number
  yield1Year: number
}

/**
 * 会话摘要
 */
export interface SessionSummary {
  overallRating: number
  recommendation: string
  keyFindings: string[]
}

/**
 * 会话消息
 */
export interface SessionMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

/**
 * 获取会话列表请求参数
 */
export interface GetSessionsParams {
  page?: number
  size?: number
  status?: AnalysisStatus
  fundCode?: string
  sortBy?: 'createdAt' | 'updatedAt'
  sortOrder?: 'asc' | 'desc'
}

/**
 * 获取会话列表
 * @param page - 页码，默认为 1
 * @param size - 每页数量，默认为 10
 * @param status - 会话状态筛选（可选）
 * @returns 分页会话列表
 */
export async function getSessions(
  page: number = 1,
  size: number = 10,
  status?: AnalysisStatus
): Promise<ApiResponse<PageResponse<SessionListItem>>> {
  const params: Record<string, string | number> = {
    page,
    size,
  }
  if (status) {
    params.status = status
  }
  return get<PageResponse<SessionListItem>>('/sessions', { params })
}

/**
 * 获取会话详情
 * @param sessionId - 会话 ID
 * @returns 会话详细信息
 */
export async function getSessionDetail(
  sessionId: string
): Promise<ApiResponse<SessionDetail>> {
  return get<SessionDetail>(`/sessions/${sessionId}`)
}

/**
 * 删除会话
 * @param sessionId - 会话 ID
 * @returns 删除结果
 */
export async function deleteSession(
  sessionId: string
): Promise<ApiResponse<null>> {
  return del<null>(`/sessions/${sessionId}`)
}

/**
 * 批量删除会话
 * @param sessionIds - 会话 ID 列表
 * @returns 删除结果
 */
export async function deleteSessions(
  sessionIds: string[]
): Promise<ApiResponse<{ deleted: number }>> {
  return del<{ deleted: number }>('/sessions', {
    params: { ids: sessionIds.join(',') },
  })
}

/**
 * 获取会话消息历史
 * @param sessionId - 会话 ID
 * @param page - 页码
 * @param size - 每页数量
 * @returns 消息历史
 */
export async function getSessionMessages(
  sessionId: string,
  page: number = 1,
  size: number = 50
): Promise<ApiResponse<PageResponse<SessionMessage>>> {
  return get<PageResponse<SessionMessage>>(`/sessions/${sessionId}/messages`, {
    params: { page, size },
  })
}

/**
 * 发送消息到会话
 * @param sessionId - 会话 ID
 * @param content - 消息内容
 * @returns AI 回复消息
 */
export async function sendMessage(
  sessionId: string,
  content: string
): Promise<ApiResponse<SessionMessage>> {
  return post<SessionMessage>(`/sessions/${sessionId}/messages`, { content })
}

/**
 * 获取用户统计数据
 * @returns 用户统计信息
 */
export async function getUserStats(): Promise<ApiResponse<UserStats>> {
  return get<UserStats>('/sessions/stats')
}

/**
 * 用户统计信息
 */
export interface UserStats {
  totalSessions: number
  completedSessions: number
  pendingSessions: number
  failedSessions: number
  recentSessions: SessionListItem[]
  favoriteFunds: FavoriteFund[]
}

/**
 * 收藏的基金
 */
export interface FavoriteFund {
  fundCode: string
  fundName: string
  analysisCount: number
  lastAnalyzedAt: string
}

export const sessionService = {
  getSessions,
  getSessionDetail,
  deleteSession,
  deleteSessions,
  getSessionMessages,
  sendMessage,
  getUserStats,
}

export default sessionService
