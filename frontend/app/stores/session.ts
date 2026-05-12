import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session } from '~/services/session.service'
import sessionService from '~/services/session.service'

/* 会话状态 Store */
export const useSessionStore = defineStore('session', () => {
  /* ========== State ========== */

  /* 会话列表 */
  const sessions = ref<Session[]>([])

  /* 当前选中的会话 */
  const currentSession = ref<Session | null>(null)

  /* 加载状态 */
  const loading = ref<boolean>(false)

  /* 错误信息 */
  const error = ref<string | null>(null)

  /* 分页信息 */
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
  })

  /* ========== Getters ========== */

  /* 最近会话（最近5条） */
  const recentSessions = computed(() => {
    return sessions.value.slice(0, 5)
  })

  /* 是否有会话 */
  const hasSessions = computed(() => {
    return sessions.value.length > 0
  })

  /* ========== Actions ========== */

  /* 获取会话列表 */
  async function fetchSessions(params?: { page?: number; pageSize?: number; keyword?: string }) {
    loading.value = true
    error.value = null

    try {
      const response = await sessionService.getSessions({
        page: params?.page || pagination.value.page,
        size: params?.pageSize || pagination.value.pageSize,
        keyword: params?.keyword,
      })

      sessions.value = response.items
      pagination.value = {
        page: response.page,
        pageSize: response.pageSize,
        total: response.total,
      }

      return { success: true, data: response }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取会话列表失败'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  /* 设置当前会话 */
  function setCurrentSession(session: Session | null) {
    currentSession.value = session
  }

  /* 根据ID选择会话 */
  async function selectSessionById(sessionId: string) {
    /* 先从本地列表查找 */
    const found = sessions.value.find(s => s.id === sessionId)
    if (found) {
      setCurrentSession(found)
      /* 对已完成或失败的会话，始终从服务器获取详情（包含 agentOutputs） */
      if (found.status === 'completed' || found.status === 'failed') {
        try {
          const session = await sessionService.getSession(sessionId)
          setCurrentSession(session)
          return { success: true, data: session }
        } catch {
          /* 获取详情失败时降级使用本地数据 */
          return { success: true, data: found }
        }
      }
      return { success: true, data: found }
    }

    /* 本地没有则从服务器获取 */
    loading.value = true
    try {
      const session = await sessionService.getSession(sessionId)
      setCurrentSession(session)
      return { success: true, data: session }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取会话详情失败'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  /* 创建新会话 */
  async function createSession(fundCode: string, riskPreference?: 'conservative' | 'neutral' | 'aggressive') {
    loading.value = true
    error.value = null

    try {
      const session = await sessionService.createSession({
        fundCode,
        riskPreference,
      })

      /* 添加到列表开头 */
      sessions.value.unshift(session)
      setCurrentSession(session)

      return { success: true, data: session }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '创建会话失败'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  /* 删除会话 */
  async function deleteSession(sessionId: string) {
    try {
      await sessionService.deleteSession(sessionId)

      /* 从列表中移除 */
      const index = sessions.value.findIndex(s => s.id === sessionId)
      if (index !== -1) {
        sessions.value.splice(index, 1)
      }

      /* 如果删除的是当前会话，清空当前会话 */
      if (currentSession.value?.id === sessionId) {
        setCurrentSession(null)
      }

      return { success: true }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '删除会话失败'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    }
  }

  /* 清空所有会话 */
  async function clearSessions() {
    loading.value = true
    error.value = null

    try {
      await sessionService.clearSessions()
      sessions.value = []
      setCurrentSession(null)
      pagination.value = { page: 1, pageSize: 20, total: 0 }
      return { success: true }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '清空会话失败'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  return {
    /* State */
    sessions,
    currentSession,
    loading,
    error,
    pagination,

    /* Getters */
    recentSessions,
    hasSessions,

    /* Actions */
    fetchSessions,
    setCurrentSession,
    selectSessionById,
    createSession,
    deleteSession,
    clearSessions,
  }
})

/* 导出类型 */
export type SessionStore = ReturnType<typeof useSessionStore>
