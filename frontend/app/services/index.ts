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

// 导出基金服务
export {
  searchFunds,
  getFundDetail,
  getFundNavHistory,
  getFundHoldings,
  getFundFees,
  getFundRanking,
  compareFunds,
  fundService,
  type FundInfo,
  type FundSearchItem,
  type FundDetail,
  type NavHistory,
  type FundHoldings,
  type StockPosition,
  type BondPosition,
  type IndustryDistribution,
  type TopHolding,
  type FundFees,
  type FeeRule,
  type SearchFundsParams,
} from './fund'

// 导出分析服务
export {
  createAnalysisSession,
  getAnalysisReport,
  getAnalysisProgress,
  cancelAnalysis,
  reanalyze,
  exportReport,
  analysisService,
  type AnalysisStatus,
  type CreateAnalysisRequest,
  type AnalysisSession,
  type AnalysisReport,
  type AnalysisSummary,
  type MultiAgentAnalysis,
  type AgentAnalysis,
  type AnalysisSignal,
  type ConsensusResult,
  type InvestmentAdvice,
  type TermAdvice,
  type PositionSizing,
  type RiskAssessment,
  type RiskFactor,
} from './analysis'

// 导出会话服务
export {
  getSessions,
  getSessionDetail,
  deleteSession,
  deleteSessions,
  getSessionMessages,
  sendMessage,
  getUserStats,
  sessionService,
  type SessionListItem,
  type SessionDetail,
  type SessionFundInfo,
  type SessionSummary,
  type SessionMessage,
  type GetSessionsParams,
  type UserStats,
  type FavoriteFund,
} from './session'

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
  fund: fundService,
  analysis: analysisService,
  session: sessionService,
  settings: settingsService,
}

export default services
