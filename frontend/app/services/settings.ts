import { get, put, post } from './api'

/* LLM 配置类型 */
export interface LLMSettings {
  apiBaseUrl: string
  apiKey: string
  model: string
  embeddingApiBaseUrl: string
  embeddingApiKey: string
  embeddingModel: string
}

/* 数据源配置类型 */
export interface DatasourceSettings {
  tushareToken: string
}

/* RAG 配置类型 */
export interface RAGSettings {
  embeddingMode: string
  topK: number
  chunkSize: number
  chunkOverlap: number
}

/* 所有配置类型 */
export interface AllSettings {
  llm: LLMSettings
  datasource: DatasourceSettings
  rag: RAGSettings
}

/* LLM 测试请求 */
export interface LLMTestRequest {
  apiBaseUrl?: string
  apiKey?: string
  model?: string
}

/* LLM 测试响应 */
export interface LLMTestResponse {
  success: boolean
  message: string
  latencyMs?: number
}

/* 获取所有配置 */
export async function getAllSettings(): Promise<AllSettings> {
  return get<AllSettings>('/settings')
}

/* 更新所有配置 */
export async function updateAllSettings(data: AllSettings): Promise<AllSettings> {
  return put<AllSettings>('/settings', data)
}

/* 获取 LLM 配置 */
export async function getLLMSettings(): Promise<LLMSettings> {
  return get<LLMSettings>('/settings/llm')
}

/* 更新 LLM 配置 */
export async function updateLLMSettings(data: LLMSettings): Promise<LLMSettings> {
  return put<LLMSettings>('/settings/llm', data)
}

/* 获取数据源配置 */
export async function getDatasourceSettings(): Promise<DatasourceSettings> {
  return get<DatasourceSettings>('/settings/datasource')
}

/* 更新数据源配置 */
export async function updateDatasourceSettings(data: DatasourceSettings): Promise<DatasourceSettings> {
  return put<DatasourceSettings>('/settings/datasource', data)
}

/* 获取 RAG 配置 */
export async function getRAGSettings(): Promise<RAGSettings> {
  return get<RAGSettings>('/settings/rag')
}

/* 更新 RAG 配置 */
export async function updateRAGSettings(data: RAGSettings): Promise<RAGSettings> {
  return put<RAGSettings>('/settings/rag', data)
}

/* 测试 LLM 连接 */
export async function testLLMConnection(request: LLMTestRequest): Promise<LLMTestResponse> {
  return post<LLMTestResponse>('/settings/llm/test', request)
}

/* 配置服务对象 */
export const settingsService = {
  getAllSettings,
  updateAllSettings,
  getLLMSettings,
  updateLLMSettings,
  getDatasourceSettings,
  updateDatasourceSettings,
  getRAGSettings,
  updateRAGSettings,
  testLLMConnection,
}

export default settingsService
