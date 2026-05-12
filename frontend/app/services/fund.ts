import { get, type ApiResponse, type PageResponse } from './api'

/**
 * 基金基本信息
 */
export interface FundInfo {
  fundCode: string
  fundName: string
  fundType: string
  fundManager: string
  fundCompany: string
  establishDate: string
  fundScale: number
  benchmark: string
  riskLevel: string
  status: string
}

/**
 * 基金搜索结果项
 */
export interface FundSearchItem {
  fundCode: string
  fundName: string
  fundType: string
  fundManager: string
  fundCompany: string
  fundScale: number
  yield1Year: number
  yield3Year: number
  yield5Year: number
}

/**
 * 基金详情
 */
export interface FundDetail extends FundInfo {
  currentNav: number
  previousNav: number
  navDate: string
  yield1Day: number
  yield1Week: number
  yield1Month: number
  yield3Month: number
  yield6Month: number
  yield1Year: number
  yield3Year: number
  yield5Year: number
  yieldFromInception: number
  maxDrawdown: number
  sharpeRatio: number
  volatility: number
  description: string
  investmentStrategy: string
}

/**
 * 净值历史记录
 */
export interface NavHistory {
  date: string
  nav: number
  accumulatedNav: number
  dailyYield: number
}

/**
 * 基金持仓信息
 */
export interface FundHoldings {
  stockPositions: StockPosition[]
  bondPositions: BondPosition[]
  industryDistribution: IndustryDistribution[]
  topHoldings: TopHolding[]
  reportDate: string
}

/**
 * 股票持仓
 */
export interface StockPosition {
  stockCode: string
  stockName: string
  shares: number
  value: number
  proportion: number
}

/**
 * 债券持仓
 */
export interface BondPosition {
  bondCode: string
  bondName: string
  value: number
  proportion: number
}

/**
 * 行业分布
 */
export interface IndustryDistribution {
  industry: string
  proportion: number
}

/**
 * 十大重仓
 */
export interface TopHolding {
  rank: number
  name: string
  code: string
  proportion: number
}

/**
 * 基金费率信息
 */
export interface FundFees {
  purchaseFee: FeeRule[]
  redemptionFee: FeeRule[]
  managementFee: number
  custodyFee: number
  serviceFee: number
}

/**
 * 费率规则
 */
export interface FeeRule {
  amountRange: string
  feeRate: number
  minFee: number
  maxFee: number
}

/**
 * 搜索基金请求参数
 */
export interface SearchFundsParams {
  keyword: string
  page?: number
  size?: number
  fundType?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

/**
 * 搜索基金
 * @param keyword - 搜索关键词（基金代码或名称）
 * @param page - 页码，默认为 1
 * @param size - 每页数量，默认为 10
 * @returns 分页搜索结果
 */
export async function searchFunds(
  keyword: string,
  page: number = 1,
  size: number = 10
): Promise<ApiResponse<PageResponse<FundSearchItem>>> {
  const params: Record<string, string | number> = {
    keyword,
    page,
    size,
  }
  return get<PageResponse<FundSearchItem>>('/funds/search', { params })
}

/**
 * 获取基金详情
 * @param fundCode - 基金代码
 * @returns 基金详细信息
 */
export async function getFundDetail(
  fundCode: string
): Promise<ApiResponse<FundDetail>> {
  return get<FundDetail>(`/funds/${fundCode}`)
}

/**
 * 获取基金净值历史
 * @param fundCode - 基金代码
 * @param startDate - 开始日期 (YYYY-MM-DD)
 * @param endDate - 结束日期 (YYYY-MM-DD)
 * @returns 净值历史记录列表
 */
export async function getFundNavHistory(
  fundCode: string,
  startDate?: string,
  endDate?: string
): Promise<ApiResponse<NavHistory[]>> {
  const params: Record<string, string> = {}
  if (startDate) {
    params.startDate = startDate
  }
  if (endDate) {
    params.endDate = endDate
  }
  return get<NavHistory[]>(`/funds/${fundCode}/nav-history`, { params })
}

/**
 * 获取基金持仓信息
 * @param fundCode - 基金代码
 * @returns 持仓详细信息
 */
export async function getFundHoldings(
  fundCode: string
): Promise<ApiResponse<FundHoldings>> {
  return get<FundHoldings>(`/funds/${fundCode}/holdings`)
}

/**
 * 获取基金费率信息
 * @param fundCode - 基金代码
 * @returns 费率详细信息
 */
export async function getFundFees(
  fundCode: string
): Promise<ApiResponse<FundFees>> {
  return get<FundFees>(`/funds/${fundCode}/fees`)
}

/**
 * 获取基金排行榜
 * @param period - 排行周期 (1m/3m/6m/1y/3y/5y)
 * @param fundType - 基金类型
 * @param limit - 返回数量
 * @returns 基金排行列表
 */
export async function getFundRanking(
  period: string = '1y',
  fundType?: string,
  limit: number = 20
): Promise<ApiResponse<FundSearchItem[]>> {
  const params: Record<string, string | number> = {
    period,
    limit,
  }
  if (fundType) {
    params.fundType = fundType
  }
  return get<FundSearchItem[]>('/funds/ranking', { params })
}

/**
 * 获取基金对比数据
 * @param fundCodes - 基金代码列表
 * @returns 对比数据
 */
export async function compareFunds(
  fundCodes: string[]
): Promise<ApiResponse<FundDetail[]>> {
  return get<FundDetail[]>('/funds/compare', {
    params: { codes: fundCodes.join(',') },
  })
}

export const fundService = {
  searchFunds,
  getFundDetail,
  getFundNavHistory,
  getFundHoldings,
  getFundFees,
  getFundRanking,
  compareFunds,
}

export default fundService
