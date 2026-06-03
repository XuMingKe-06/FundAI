/**
 * API 服务层统一导出
 * 提供所有 API 服务的统一入口
 */

// 导出 API 核心模块
export {
  apiClient,
  get,
  post,
  put,
  del,
  patch,
  type ApiResponse,
  type PageResponse,
  type ApiError,
} from './api'

// 导出分析服务
export {
  analysisService,
  type AnalysisReport,
  type CreateAnalysisParams,
} from './analysis.service'

// 导出会话服务
export {
  sessionService,
  type Session,
  type AgentOutputItem,
  type SessionListParams,
  type CreateSessionParams,
} from './session.service'

// 导出配置服务
export {
  getAllSettings,
  updateAllSettings,
  getLLMSettings,
  updateLLMSettings,
  getDatasourceSettings,
  updateDatasourceSettings,
  testLLMConnection,
  settingsService,
  type LLMSettings,
  type DatasourceSettings,
  type RAGSettings,
  type AllSettings,
  type LLMTestRequest,
  type LLMTestResponse,
} from './settings'

/**
 * 服务实例统一导出
 * 便于在组件中直接使用
 */
export const services = {
  analysis: analysisService,
  session: sessionService,
  settings: settingsService,
}

export default services
