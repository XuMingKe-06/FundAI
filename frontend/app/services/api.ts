import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

/* 将 snake_case 字符串转换为 camelCase */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())
}

/* 将 camelCase 字符串转换为 snake_case */
function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
}

/* 递归转换对象中的 snake_case 键为 camelCase */
function transformKeys<T>(obj: T): T {
  if (obj === null || obj === undefined) {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => transformKeys(item)) as T
  }

  if (typeof obj === 'object' && obj.constructor === Object) {
    const result: Record<string, unknown> = {}
    for (const key of Object.keys(obj as Record<string, unknown>)) {
      const camelKey = snakeToCamel(key)
      result[camelKey] = transformKeys((obj as Record<string, unknown>)[key])
    }
    return result as T
  }

  return obj
}

/* 递归转换对象中的 camelCase 键为 snake_case */
function transformKeysToSnake<T>(obj: T): T {
  if (obj === null || obj === undefined) {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => transformKeysToSnake(item)) as T
  }

  if (typeof obj === 'object' && obj.constructor === Object) {
    const result: Record<string, unknown> = {}
    for (const key of Object.keys(obj as Record<string, unknown>)) {
      const snakeKey = camelToSnake(key)
      result[snakeKey] = transformKeysToSnake((obj as Record<string, unknown>)[key])
    }
    return result as T
  }

  return obj
}

/* 开发环境标识 */
const isDev = import.meta.dev

/* 差异化超时配置 */
const TIMEOUT_CONFIG = {
  analysis: 120000,  // 分析相关接口 120s
  query: 15000,      // 普通查询接口 15s
  default: 30000,    // 默认超时 30s
} as const

/* 分析相关 URL 模式 */
const ANALYSIS_URL_PATTERNS = ['/analysis/', '/sessions/']
/* 普通查询 URL 模式 */
const QUERY_URL_PATTERNS = ['/funds/search', '/funds/', '/knowledge/']

/** 根据 URL 自动匹配超时时间 */
function getTimeoutByUrl(url: string): number {
  if (ANALYSIS_URL_PATTERNS.some(p => url?.includes(p))) return TIMEOUT_CONFIG.analysis
  if (QUERY_URL_PATTERNS.some(p => url?.includes(p))) return TIMEOUT_CONFIG.query
  return TIMEOUT_CONFIG.default
}

/* 重试配置 */
const RETRY_CONFIG = {
  maxRetries: 3,     // 最大重试次数
  baseDelay: 1000,   // 基础延迟 1s
  maxDelay: 10000,   // 最大延迟 10s
} as const

/** 判断错误是否可重试（仅网络错误和 5xx，不重试 4xx） */
function isRetryableError(error: any): boolean {
  if (!error.response) return true
  const status = error.response.status
  return status >= 500 && status < 600
}

/** 计算指数退避延迟 */
function getRetryDelay(retryCount: number): number {
  const delay = RETRY_CONFIG.baseDelay * Math.pow(2, retryCount)
  return Math.min(delay, RETRY_CONFIG.maxDelay)
}

/* API 响应通用结构 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/* 分页响应结构 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/* 创建 axios 实例 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  /* 请求拦截器 - 差异化超时 + 键名转换 + 开发日志 */
  client.interceptors.request.use(
    (config) => {
      config.timeout = getTimeoutByUrl(config.url || '')
      if (config.data && typeof config.data === 'object') {
        config.data = transformKeysToSnake(config.data)
      }
      if (config.params && typeof config.params === 'object') {
        config.params = transformKeysToSnake(config.params)
      }
      if (isDev) {
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
        if (config.params) {
          console.log('[API Request Params]', config.params)
        }
        if (config.data) {
          console.log('[API Request Data]', config.data)
        }
      }
      return config
    },
    (error) => {
      if (isDev) {
        console.log('[API Error] Request failed:', error.message)
      }
      return Promise.reject(error)
    }
  )

  /* 响应拦截器 - 键名转换 + 开发日志 */
  client.interceptors.response.use(
    (response) => {
      if (isDev) {
        console.log(`[API Response] ${response.status} ${response.config.baseURL}${response.config.url}`)
        console.log('[API Response Data]', response.data)
      }
      response.data = transformKeys(response.data)
      return response
    },
    (error) => {
      if (isDev) {
        if (error.response) {
          console.log(`[API Error] ${error.response.status} ${error.config?.baseURL}${error.config?.url}`)
          console.log('[API Error] Response data:', error.response.data)
          console.log('[API Error] Message:', error.message)
        } else if (error.request) {
          console.log('[API Error] No response received')
          console.log('[API Error] Message:', error.message)
        } else {
          console.log('[API Error] Request setup error:', error.message)
        }
      }
      return Promise.reject(error)
    }
  )

  return client
}

/* API 客户端实例 */
export const apiClient = createApiClient()

/* 通用请求方法（支持重试 + AbortController 取消） */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  let lastError: any = null

  for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
    try {
      const response: AxiosResponse<ApiResponse<T>> = await apiClient.request(config)
      return response.data.data
    } catch (error: any) {
      lastError = error

      /* 请求被取消、不可重试的错误（4xx）、已达最大重试次数，直接抛出 */
      if (axios.isCancel(error) || !isRetryableError(error) || attempt >= RETRY_CONFIG.maxRetries) {
        throw error
      }

      const delay = getRetryDelay(attempt)
      if (isDev) {
        console.log(`[API Retry] 第${attempt + 1}次重试，${delay}ms 后执行: ${config.url}`)
      }
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }

  throw lastError
}

/* GET 请求 */
export async function get<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'GET', url, params, ...config })
}

/* POST 请求 */
export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'POST', url, data, ...config })
}

/* PUT 请求 */
export async function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'PUT', url, data, ...config })
}

/* DELETE 请求 */
export async function del<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'DELETE', url, params, ...config })
}

/* PATCH 请求 */
export async function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'PATCH', url, data, ...config })
}

/* 分页响应结构（兼容旧接口） */
export type PageResponse<T> = PaginatedResponse<T>

/* API 错误类型 */
export interface ApiError {
  code: number
  message: string
  detail?: string
}

export default apiClient
