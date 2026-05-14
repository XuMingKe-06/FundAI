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

  /* 请求拦截器 - 将 camelCase 转换为 snake_case + 记录请求日志 */
  client.interceptors.request.use(
    (config) => {
      /* 将请求数据中的 camelCase 键名转换为 snake_case */
      if (config.data && typeof config.data === 'object') {
        config.data = transformKeysToSnake(config.data)
      }
      /* 将请求参数中的 camelCase 键名转换为 snake_case */
      if (config.params && typeof config.params === 'object') {
        config.params = transformKeysToSnake(config.params)
      }
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
      if (config.params) {
        console.log('[API Request Params]', config.params)
      }
      if (config.data) {
        console.log('[API Request Data]', config.data)
      }
      return config
    },
    (error) => {
      console.log('[API Error] Request failed:', error.message)
      return Promise.reject(error)
    }
  )

  /* 响应拦截器 - 键名转换 + 错误日志 */
  client.interceptors.response.use(
    (response) => {
      /* 输出响应日志 */
      console.log(`[API Response] ${response.status} ${response.config.baseURL}${response.config.url}`)
      console.log('[API Response Data]', response.data)

      /* 将响应数据中的 snake_case 键名转换为 camelCase */
      response.data = transformKeys(response.data)
      return response
    },
    (error) => {
      /* 输出错误日志 */
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

      return Promise.reject(error)
    }
  )

  return client
}

/* API 客户端实例 */
export const apiClient = createApiClient()

/* 通用请求方法 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response: AxiosResponse<ApiResponse<T>> = await apiClient.request(config)
  return response.data.data
}

/* GET 请求 */
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>({ method: 'GET', url, params })
}

/* POST 请求 */
export async function post<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ method: 'POST', url, data })
}

/* PUT 请求 */
export async function put<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ method: 'PUT', url, data })
}

/* DELETE 请求 */
export async function del<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>({ method: 'DELETE', url, params })
}

/* PATCH 请求 */
export async function patch<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ method: 'PATCH', url, data })
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
