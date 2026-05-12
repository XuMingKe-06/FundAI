import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

/* 将 snake_case 字符串转换为 camelCase */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())
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

  /* 请求拦截器 - 添加认证 token 和调试日志 */
  client.interceptors.request.use(
    (config) => {
      /* 输出请求日志 */
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
      if (config.params) {
        console.log('[API Request Params]', config.params)
      }
      if (config.data) {
        console.log('[API Request Data]', config.data)
      }

      /* 从 localStorage 获取 token */
      if (import.meta.client) {
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      }
      return config
    },
    (error) => {
      console.log('[API Error] Request failed:', error.message)
      return Promise.reject(error)
    }
  )

  /* 响应拦截器 - 处理键名转换、错误和 token 刷新 */
  client.interceptors.response.use(
    (response) => {
      /* 输出响应日志 */
      console.log(`[API Response] ${response.status} ${response.config.baseURL}${response.config.url}`)
      console.log('[API Response Data]', response.data)

      response.data = transformKeys(response.data)
      return response
    },
    async (error) => {
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

      const originalRequest = error.config

      /* 如果是 401 错误且未尝试过刷新 token */
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true

        /* 检查是否是公开接口（不需要认证的接口） */
        const publicEndpoints = [
          '/auth/send-code',
          '/auth/login',
          '/auth/refresh',
          '/auth/check-token',
          '/funds/search',
        ]
        const isPublicEndpoint = publicEndpoints.some(endpoint => 
          originalRequest.url?.includes(endpoint)
        )

        /* 如果是公开接口，直接返回错误，不尝试刷新 token */
        if (isPublicEndpoint) {
          console.log('[API] Public endpoint returned 401, not retrying')
          return Promise.reject(error)
        }

        try {
          /* 尝试刷新 token */
          if (import.meta.client) {
            const refreshToken = localStorage.getItem('refreshToken')
            if (refreshToken) {
              console.log('[API] Attempting to refresh token...')
              const response = await axios.post('/api/v1/auth/refresh', {
                refresh_token: refreshToken,
              }, {
                timeout: 10000, /* 刷新token请求超时时间设为10秒 */
              })
              const { accessToken } = transformKeys(response.data.data)
              localStorage.setItem('token', accessToken)
              originalRequest.headers.Authorization = `Bearer ${accessToken}`
              console.log('[API] Token refresh successful, retrying request...')
              return client(originalRequest)
            }
          }
        } catch (refreshError) {
          /* 刷新失败，清除登录状态 */
          console.log('[API Error] Token refresh failed:', refreshError)
          if (import.meta.client) {
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            localStorage.removeItem('user')
            /* 不自动跳转，让页面自己处理未登录状态 */
          }
        }
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
