import { get, post } from './api'

/* 用户信息类型 - 与后端 UserInfo 对齐，使用 camelCase */
export interface User {
  id: string
  phone: string
  username?: string
  email?: string
  role: string
  riskPreference: string
  isActive: boolean
  createdAt: string
  lastLoginAt?: string
}

/* 登录请求参数 */
export interface LoginParams {
  phone: string
  code: string
}

/* 登录响应 - 与后端 LoginResponse 对齐，使用 camelCase */
export interface LoginResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
  refreshToken: string
  user: User
}

/* 刷新令牌响应 - 与后端 RefreshTokenResponse 对齐，使用 camelCase */
export interface RefreshTokenResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

/* 发送验证码参数 */
export interface SendCodeParams {
  phone: string
}

/* 发送验证码响应 */
export interface SendCodeResponse {
  success: boolean
  expireIn: number
}

/* 发送验证码 */
export async function sendVerificationCode(params: SendCodeParams): Promise<SendCodeResponse> {
  return post<SendCodeResponse>('/auth/send-code', params)
}

/* 登录 */
export async function login(params: LoginParams): Promise<LoginResponse> {
  return post<LoginResponse>('/auth/login', params)
}

/* 登出 */
export async function logout(): Promise<void> {
  await post('/auth/logout')
}

/* 刷新 token */
export async function refreshToken(token: string): Promise<RefreshTokenResponse> {
  return post<RefreshTokenResponse>('/auth/refresh', { refresh_token: token })
}

/* 获取当前用户信息 */
export async function getCurrentUser(): Promise<User> {
  return get<User>('/auth/me')
}

/* 检查是否已认证 */
export function isAuthenticated(): boolean {
  if (import.meta.client) {
    return !!localStorage.getItem('token')
  }
  return false
}

/* 更新用户信息 */
export async function updateUser(data: Partial<User>): Promise<User> {
  return post<User>('/auth/update', data)
}

/* 认证服务对象 */
export const authService = {
  sendVerificationCode,
  sendCode: sendVerificationCode,
  login,
  logout,
  refreshToken,
  getCurrentUser,
  updateUser,
  isAuthenticated,
}

export default authService
