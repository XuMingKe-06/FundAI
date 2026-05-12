import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AnalysisReport } from '~/services/analysis.service'
import analysisService from '~/services/analysis.service'

/* 分析报告状态 Store */
export const useAnalysisStore = defineStore('analysis', () => {
  /* ========== State ========== */

  /* 当前分析报告 */
  const currentReport = ref<AnalysisReport | null>(null)

  /* 加载状态 */
  const loading = ref<boolean>(false)

  /* 错误信息 */
  const error = ref<string | null>(null)

  /* 分析进度（0-100） */
  const progress = ref<number>(0)

  /* SSE 连接实例 */
  const eventSource = ref<EventSource | null>(null)

  /* 分析是否暂停 */
  const isPaused = ref<boolean>(false)

  /* 暂停状态持久化键名前缀 */
  const PAUSED_SESSION_KEY = 'fundai_paused_session'

  /* 从 sessionStorage 恢复暂停状态，返回是否为暂停状态 */
  function restorePauseState(sessionId: string): boolean {
    if (!import.meta.client) return false
    const pausedId = sessionStorage.getItem(PAUSED_SESSION_KEY)
    const paused = pausedId === sessionId
    isPaused.value = paused
    return paused
  }

  /* 保存暂停状态到 sessionStorage */
  function savePauseState(sessionId: string | undefined) {
    if (!import.meta.client) return
    if (sessionId) {
      sessionStorage.setItem(PAUSED_SESSION_KEY, sessionId)
    } else {
      sessionStorage.removeItem(PAUSED_SESSION_KEY)
    }
  }

  /* 清除暂停状态 */
  function clearPauseState() {
    if (!import.meta.client) return
    sessionStorage.removeItem(PAUSED_SESSION_KEY)
  }

  /* ========== Getters ========== */

  /* 是否有报告 */
  const hasReport = computed(() => {
    return currentReport.value !== null
  })

  /* 是否正在分析 */
  const isAnalyzing = computed(() => {
    return loading.value && progress.value > 0 && progress.value < 100
  })

  /* 是否分析完成 */
  const isCompleted = computed(() => {
    return progress.value === 100 && currentReport.value !== null
  })

  /* 获取决策概览 */
  const decisionOverview = computed(() => {
    return currentReport.value?.decision || null
  })

  /* 获取评分数据 */
  const scores = computed(() => {
    return currentReport.value?.scores || null
  })

  /* 获取成本矩阵 */
  const costMatrix = computed(() => {
    return currentReport.value?.costMatrix || []
  })

  /* ========== Actions ========== */

  /* 暂停分析 */
  function pauseAnalysis(sessionId?: string) {
    isPaused.value = true
    savePauseState(sessionId)
  }

  /* 继续分析 */
  function resumeAnalysis() {
    isPaused.value = false
    clearPauseState()
  }

  /* 创建分析任务 */
  async function createAnalysis(
    fundCode: string,
    riskPreference?: 'conservative' | 'neutral' | 'aggressive',
    previousSessionId?: string,
    analysisMode?: 'parallel' | 'sequential'
  ) {
    loading.value = true
    error.value = null
    progress.value = 0
    currentReport.value = null

    try {
      const result = await analysisService.createAnalysis({
        fundCode,
        riskPreference,
        previousSessionId,
        analysisMode,
      })

      return { success: true, data: result }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '创建分析任务失败'
      error.value = errorMessage
      loading.value = false
      return { success: false, error: errorMessage }
    }
  }

  /* 获取分析报告 */
  async function fetchReport(sessionId: string) {
    loading.value = true
    error.value = null

    try {
      const report = await analysisService.getReport(sessionId)
      currentReport.value = report
      progress.value = 100
      return { success: true, data: report }
    } catch (err) {
      let errorMessage = '获取分析报告失败'
      
      /* 检查是否是404错误 */
      if (err instanceof Error) {
        if (err.message.includes('404')) {
          errorMessage = '分析报告尚未生成，请等待分析完成或重新分析'
        } else {
          errorMessage = err.message
        }
      }
      
      error.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  /* 订阅分析进度流 */
  function subscribeAnalysisProgress(sessionId: string) {
    /* 关闭之前的连接 */
    unsubscribeAnalysisProgress()

    const es = analysisService.getAnalysisStream(sessionId)
    if (!es) return

    eventSource.value = es

    /* 连接成功 */
    es.onopen = () => {
      progress.value = 0
    }

    /* 接收消息 */
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'progress':
            /* 更新进度 */
            progress.value = data.progress
            break

          case 'agent_update':
            /* 智能体状态更新，由 agent store 处理 */
            break

          case 'complete':
            /* 分析完成 */
            progress.value = 100
            if (data.report) {
              currentReport.value = data.report
            }
            unsubscribeAnalysisProgress()
            break

          case 'error':
            /* 分析错误 */
            error.value = data.message
            unsubscribeAnalysisProgress()
            break
        }
      } catch {
        /* 解析失败，忽略 */
      }
    }

    /* 连接错误 */
    es.onerror = () => {
      error.value = '分析进度连接失败'
      unsubscribeAnalysisProgress()
    }
  }

  /* 取消订阅分析进度 */
  function unsubscribeAnalysisProgress() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
  }

  /* 清除报告 */
  function clearReport() {
    currentReport.value = null
    error.value = null
    progress.value = 0
    isPaused.value = false
    clearPauseState()
    unsubscribeAnalysisProgress()
  }

  /* 搜索基金 */
  async function searchFunds(keyword: string) {
    try {
      const results = await analysisService.searchFunds(keyword)
      return { success: true, data: results }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '搜索基金失败'
      return { success: false, error: errorMessage }
    }
  }

  return {
    /* State */
    currentReport,
    loading,
    error,
    progress,
    isPaused,

    /* Getters */
    hasReport,
    isAnalyzing,
    isCompleted,
    decisionOverview,
    scores,
    costMatrix,

    /* Actions */
    pauseAnalysis,
    resumeAnalysis,
    restorePauseState,
    savePauseState,
    clearPauseState,
    createAnalysis,
    fetchReport,
    subscribeAnalysisProgress,
    unsubscribeAnalysisProgress,
    clearReport,
    searchFunds,
  }
})

/* 导出类型 */
export type AnalysisStore = ReturnType<typeof useAnalysisStore>
