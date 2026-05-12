import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '~/services/auth'
import { authService } from '~/services/auth'

/* 认证状态 Store */
export const useAuthStore = defineStore('auth', () => {
  /* ========== State ========== */

  /* 用户信息 */
  const user = ref<User | null>(null)

  /* 访问令牌 */
  const token = ref<string | null>(null)

  /* 刷新令牌 */
  const refreshToken = ref<string | null>(null)

  /* 是否已认证 */
  const isAuthenticated = ref<boolean>(false)

  /* 发送验证码错误信息 */
  const sendCodeError = ref<string | null>(null)

  /* ========== Getters ========== */

  /* 是否已登录 */
  const isLoggedIn = computed(() => {
    return isAuthenticated.value && token.value !== null
  })

  /* 用户角色 */
  const userRole = computed(() => {
    return user.value?.role || null
  })

  /* ========== Actions ========== */

  /* 解析 JWT token 获取 payload，不验证签名（仅用于读取过期时间） */
  function parseJwtPayload(token: string): Record<string, unknown> | null {
    try {
      const parts = token.split('.')
      if (parts.length !== 3 || !parts[1]) return null
      const payload = parts[1]
      /* Base64Url 解码 */
      const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
      const jsonStr = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      return JSON.parse(jsonStr)
    } catch {
      return null
    }
  }

  /* 检查 token 是否已过期（本地判断，不依赖后端） */
  function isTokenExpired(token: string): boolean {
    const payload = parseJwtPayload(token)
    if (!payload || !payload.exp) return true
    /* exp 是秒级时间戳，留 30 秒缓冲 */
    const expireTime = (payload.exp as number) * 1000 - 30 * 1000
    return Date.now() >= expireTime
  }

  /* 从本地存储恢复登录状态 */
  async function restoreAuth() {
    if (import.meta.client) {
      const savedToken = localStorage.getItem('token')
      const savedRefreshToken = localStorage.getItem('refreshToken')
      const savedUser = localStorage.getItem('user')

      if (savedToken && savedUser) {
        /* 检查 access token 是否已过期 */
        if (isTokenExpired(savedToken)) {
          /* access token 已过期，尝试用 refresh token 刷新 */
          if (savedRefreshToken && !isTokenExpired(savedRefreshToken)) {
            try {
              const response = await authService.refreshToken(savedRefreshToken)
              /* 刷新成功，更新 token */
              token.value = response.accessToken
              refreshToken.value = savedRefreshToken
              user.value = JSON.parse(savedUser)
              isAuthenticated.value = true
              localStorage.setItem('token', response.accessToken)
            } catch {
              /* 刷新失败，清除登录状态 */
              setUser(null)
              setToken(null, null)
              isAuthenticated.value = false
            }
          } else {
            /* refresh token 也过期了，清除登录状态 */
            setUser(null)
            setToken(null, null)
            isAuthenticated.value = false
          }
        } else {
          /* access token 仍有效，直接恢复 */
          token.value = savedToken
          refreshToken.value = savedRefreshToken
          user.value = JSON.parse(savedUser)
          isAuthenticated.value = true
        }
      }
    }
  }

  /* 设置用户信息 */
  function setUser(userData: User | null) {
    user.value = userData
    if (import.meta.client) {
      if (userData) {
        localStorage.setItem('user', JSON.stringify(userData))
      } else {
        localStorage.removeItem('user')
      }
    }
  }

  /* 设置令牌 */
  function setToken(newToken: string | null, newRefreshToken?: string | null) {
    token.value = newToken
    if (newRefreshToken !== undefined) {
      refreshToken.value = newRefreshToken
    }

    if (import.meta.client) {
      if (newToken) {
        localStorage.setItem('token', newToken)
        if (newRefreshToken) {
          localStorage.setItem('refreshToken', newRefreshToken)
        }
      } else {
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
      }
    }
  }

  /* 登录 */
  async function login(phone: string, code: string) {
    try {
      const response = await authService.login({ phone, code })

      /* 保存登录信息 */
      setUser(response.user)
      setToken(response.accessToken, response.refreshToken)
      isAuthenticated.value = true

      return { success: true, data: response }
    } catch (error) {
      return { success: false, error }
    }
  }

  /* 登出 */
  async function logout() {
    try {
      await authService.logout()
    } catch {
      /* 忽略登出接口错误 */
    } finally {
      /* 清除本地状态 */
      setUser(null)
      setToken(null, null)
      isAuthenticated.value = false
    }
  }

  /* 刷新令牌 */
  async function refreshAccessToken() {
    if (!refreshToken.value) {
      return { success: false, error: new Error('No refresh token') }
    }

    try {
      const response = await authService.refreshToken(refreshToken.value)
      setToken(response.accessToken)
      return { success: true, data: response }
    } catch (error) {
      /* 刷新失败，清除登录状态 */
      await logout()
      return { success: false, error }
    }
  }

  /* 更新用户信息 */
  async function updateUserInfo(data: Partial<User>) {
    try {
      const updatedUser = await authService.updateUser(data)
      setUser(updatedUser)
      return { success: true, data: updatedUser }
    } catch (error) {
      return { success: false, error }
    }
  }

  /* 发送验证码 */
  async function sendVerificationCode(phone: string) {
    try {
      sendCodeError.value = null
      await authService.sendCode({ phone })
      return true
    } catch (error: any) {
      sendCodeError.value = error?.message || '发送验证码失败'
      return false
    }
  }

  /* 初始化时恢复登录状态 */
  if (import.meta.client) {
    restoreAuth()
  }

  return {
    /* State */
    user,
    token,
    refreshToken,
    isAuthenticated,
    sendCodeError,

    /* Getters */
    isLoggedIn,
    userRole,

    /* Actions */
    login,
    logout,
    setUser,
    setToken,
    refreshAccessToken,
    updateUserInfo,
    restoreAuth,
    sendVerificationCode,
  }
})

/* 导出类型 */
export type AuthStore = ReturnType<typeof useAuthStore>
