/**
 * 工作台分析流程管理组合式函数
 *
 * 封装分析创建、重试、暂停/继续、会话选择等业务逻辑
 * 图表管理由 WorkspaceReportView 组件内部处理
 */

import { useAgentStore, type AgentType } from '~/stores/agent'
import { useAnalysisStore } from '~/stores/analysis'
import { useSessionStore } from '~/stores/session'
import { useAnalysisSettings, type AnalysisMode } from '~/composables/useAnalysisSettings'
import sessionService from '~/services/session.service'
import type { Ref } from 'vue'

/* 分析流程组合式函数的配置选项 */
export interface UseWorkspaceAnalysisOptions {
  headerFundInput: Ref<string>
  hasAutoSelectedAgent: Ref<boolean>
  currentView: Ref<'report' | 'agent'>
  connectToAnalysisStream: (sessionId: string) => void
  disconnectSSE: () => void
  markStreamEnded: () => void
}

export function useWorkspaceAnalysis(options: UseWorkspaceAnalysisOptions) {
  const {
    headerFundInput,
    hasAutoSelectedAgent,
    currentView,
    connectToAnalysisStream,
    disconnectSSE,
    markStreamEnded,
  } = options

  const agentStore = useAgentStore()
  const analysisStore = useAnalysisStore()
  const sessionStore = useSessionStore()
  const { analysisMode } = useAnalysisSettings()

  const route = useRoute()
  const router = useRouter()

  /* 当前分析报告 */
  const currentReport = computed(() => analysisStore.currentReport)

  /* 是否正在分析 */
  const isAnalyzing = computed(() => analysisStore.isAnalyzing || agentStore.runningAgents.length > 0)

  /* 是否可以重新分析 */
  const canReanalyze = computed(() =>
    sessionStore.currentSession?.status === 'completed'
  )

  /* 查找同一基金代码的已完成会话 */
  function findCompletedSessionByFundCode(fundCode: string) {
    return sessionStore.sessions.find(
      s => s.fundCode === fundCode && s.status === 'completed'
    )
  }

  /* 加载分析报告 */
  async function loadAnalysisReport(sessionId: string) {
    const result = await analysisStore.fetchReport(sessionId)
    if (!result.success) {
      /* 如果是404错误，显示报告未生成的提示 */
      if (result.error?.includes('404') || result.error?.includes('尚未生成')) {
        analysisStore.error = '分析报告尚未生成，请重新分析'
      }
    }
  }

  /* 开始新分析 */
  async function startNewAnalysis() {
    const fundCode = headerFundInput.value.trim()
    if (!fundCode) {
      ElMessage.warning('请输入基金代码或名称')
      return
    }

    /* 检测该基金是否已有分析记录 */
    const existingSession = findCompletedSessionByFundCode(fundCode)
    if (existingSession) {
      try {
        await ElMessageBox.confirm(
          `基金 ${fundCode} 已有分析记录，是否基于上次分析结果重新分析？`,
          '重新分析确认',
          { confirmButtonText: '重新分析', cancelButtonText: '取消', type: 'warning' }
        )
      } catch {
        /* 用户取消 */
        return
      }
    }

    /* 重置智能体状态 */
    agentStore.resetAgents()
    analysisStore.clearReport()

    /* 重置自动选中标志 */
    hasAutoSelectedAgent.value = false

    /* 创建分析会话（如有前次会话，传入 previousSessionId 和分析模式） */
    const createResult = await analysisStore.createAnalysis(
      fundCode, undefined, existingSession?.id, analysisMode.value
    )
    if (!createResult.success) {
      ElMessage.error(createResult.error || '创建分析任务失败')
      return
    }

    const sessionId = createResult.data?.sessionId
    if (!sessionId) {
      ElMessage.error('创建分析任务失败：未获取到会话ID')
      return
    }

    /* 立即将会话添加到左侧栏 */
    const newSession = {
      id: sessionId,
      fundCode: fundCode,
      fundName: createResult.data?.fundName || fundCode,
      status: 'running',
      decision: '分析中',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    sessionStore.sessions.unshift(newSession)
    sessionStore.setCurrentSession(newSession)

    /* 将会话 ID 保存到 URL，支持刷新恢复 */
    router.replace({ query: { ...route.query, session: sessionId } })

    /* 连接 SSE 流开始分析 */
    connectToAnalysisStream(sessionId)
  }

  /* 从右侧栏重新分析 */
  async function startReanalysis() {
    const current = sessionStore.currentSession
    if (!current) return

    try {
      await ElMessageBox.confirm(
        `确定要重新分析基金 ${current.fundCode} 吗？新的分析将参考本次分析结果。`,
        '重新分析确认',
        { confirmButtonText: '重新分析', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      /* 用户取消 */
      return
    }

    headerFundInput.value = current.fundCode
    agentStore.resetAgents()
    analysisStore.clearReport()
    hasAutoSelectedAgent.value = false

    /* 创建新分析，传入当前会话ID作为 previousSessionId 和分析模式 */
    const createResult = await analysisStore.createAnalysis(
      current.fundCode, undefined, current.id, analysisMode.value
    )
    if (!createResult.success) {
      ElMessage.error(createResult.error || '创建分析任务失败')
      return
    }

    const sessionId = createResult.data?.sessionId
    if (!sessionId) {
      ElMessage.error('创建分析任务失败：未获取到会话ID')
      return
    }

    const newSession = {
      id: sessionId,
      fundCode: current.fundCode,
      fundName: createResult.data?.fundName || current.fundCode,
      status: 'running',
      decision: '分析中',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    sessionStore.sessions.unshift(newSession)
    sessionStore.setCurrentSession(newSession)

    /* 将会话 ID 保存到 URL，支持刷新恢复 */
    router.replace({ query: { ...route.query, session: sessionId } })

    connectToAnalysisStream(sessionId)
  }

  /* 暂停/继续分析切换 */
  function togglePauseAnalysis() {
    if (analysisStore.isPaused) {
      /* 继续分析：重新连接 SSE 流 */
      analysisStore.resumeAnalysis()
      const sessionId = sessionStore.currentSession?.id
      if (sessionId) {
        connectToAnalysisStream(sessionId)
      }
      ElMessage.info('分析已继续')
    } else {
      /* 暂停分析：断开 SSE 连接 */
      const sessionId = sessionStore.currentSession?.id
      analysisStore.pauseAnalysis(sessionId)
      disconnectSSE()
      ElMessage.info('分析已暂停')
    }
  }

  /* 选择会话 */
  async function selectChat(sessionId: string) {
    /* 清除之前的错误信息 */
    analysisStore.error = null

    /* 并行获取会话详情和报告 */
    const [sessionResult, reportResult] = await Promise.all([
      sessionService.getSession(sessionId).catch(() => null),
      analysisStore.fetchReport(sessionId)
    ])

    if (!sessionResult) {
      /* 会话获取失败，尝试从本地列表查找兜底 */
      const localSession = sessionStore.sessions.find(s => s.id === sessionId)
      if (localSession) {
        sessionStore.setCurrentSession(localSession)
      }
      return
    }

    /* 设置当前会话 */
    sessionStore.setCurrentSession(sessionResult as any)

    /* 将会话 ID 保存到 URL，支持刷新恢复 */
    router.replace({ query: { ...route.query, session: sessionId } })

    if (sessionResult.status === 'completed') {
      /* 使用 setTimeout(0) 延迟重型 CPU 工作，让首帧先渲染 */
      const agentOutputs = (sessionResult as any).agentOutputs as Array<any> | undefined
      setTimeout(() => {
        if (agentOutputs && agentOutputs.length > 0) {
          agentStore.restoreFromSessionData(agentOutputs)
        } else {
          /* 兜底：仅标记所有智能体为已完成以显示状态颜色 */
          agentStore.restoreFromSessionData([
            { agentType: 'fundamental', status: 'completed' },
            { agentType: 'technical', status: 'completed' },
            { agentType: 'risk', status: 'completed' },
            { agentType: 'cost', status: 'completed' },
            { agentType: 'sentiment', status: 'completed' },
            { agentType: 'decision', status: 'completed' },
          ])
        }
      }, 0)

      /* 报告已在上面并行获取，检查结果 */
      if (!reportResult.success) {
        if (reportResult.error?.includes('404') || reportResult.error?.includes('尚未生成')) {
          analysisStore.error = '分析报告尚未生成，请重新分析'
        }
      }
    } else if (sessionResult.status === 'running') {
      /* 运行中的会话：尝试恢复已有智能体输出，连接 SSE 流继续接收分析进度 */

      /* 先恢复暂停状态（在 clearReport 之前，因为 clearReport 会清除 sessionStorage） */
      const wasPaused = analysisStore.restorePauseState(sessionId)

      analysisStore.clearReport()
      analysisStore.loading = true
      analysisStore.progress = 1
      hasAutoSelectedAgent.value = false

      /* clearReport 会重置 isPaused，需要重新设置暂停状态 */
      if (wasPaused) {
        analysisStore.isPaused = true
        /* 重新保存暂停状态到 sessionStorage（clearReport 会清除它） */
        analysisStore.savePauseState(sessionId)
      }

      const agentOutputs = (sessionResult as any).agentOutputs
      if (agentOutputs && agentOutputs.length > 0) {
        agentStore.restoreFromSessionData(agentOutputs)
      } else {
        agentStore.resetAgents()
      }

      /* 仅在未暂停时重连 SSE 流 */
      if (!analysisStore.isPaused) {
        connectToAnalysisStream(sessionId)
      }
    } else {
      /* 其他状态重置智能体，清空报告 */
      agentStore.resetAgents()
      analysisStore.clearReport()
      if (sessionResult.status === 'failed') {
        analysisStore.error = '该分析任务执行失败，请重新分析'
      } else {
        analysisStore.error = '该分析任务尚未完成'
      }
    }
  }

  /* 显示智能体详情（图表由 ReportView 组件的 onUnmounted 自动销毁） */
  function showAgentDetail(agentType: AgentType) {
    agentStore.setCurrentAgent(agentType)
    currentView.value = 'agent'
  }

  /* 显示报告视图（图表由 ReportView 组件的 onMounted 自动初始化） */
  function showReportView() {
    currentView.value = 'report'
  }

  /* 重试加载 */
  function retryLoad() {
    const sessionId = sessionStore.currentSession?.id
    const sessionStatus = sessionStore.currentSession?.status

    if (!sessionId) return

    if (sessionStatus === 'failed' || sessionStatus === 'pending') {
      /* 失败或待分析的会话，重新发起分析 */
      const fundCode = sessionStore.currentSession?.fundCode || headerFundInput.value
      if (fundCode) {
        headerFundInput.value = fundCode
        startNewAnalysis()
      }
    } else if (sessionStatus === 'running') {
      /* 运行中的会话，重新连接 SSE 流 */
      analysisStore.clearReport()
      analysisStore.loading = true
      analysisStore.progress = 1
      analysisStore.error = null
      agentStore.resetAgents()
      connectToAnalysisStream(sessionId)
    } else {
      /* 已完成或其他状态，尝试重新加载报告 */
      loadAnalysisReport(sessionId)
    }
  }

  /* 页面初始化逻辑（已移除认证检查） */
  async function initPage() {
    /* 从URL参数获取基金代码 */
    const fund = route.query.fund as string
    if (fund) {
      headerFundInput.value = fund
    }

    /* 加载会话列表 */
    const sessionsResult = await sessionStore.fetchSessions()

    /* 在后台异步加载会话详情与报告，不阻塞首次渲染 */
    if (sessionsResult.success && sessionStore.hasSessions && sessionStore.sessions.length > 0) {
      /* 优先从 URL 参数恢复会话，否则选择第一个会话 */
      const sessionIdFromUrl = route.query.session as string
      const targetSession = sessionIdFromUrl
        ? sessionStore.sessions.find(s => s.id === sessionIdFromUrl)
        : null
      const sessionId = targetSession?.id || sessionStore.sessions[0].id
      selectChat(sessionId).catch(() => {})
    }
  }

  return {
    currentReport,
    isAnalyzing,
    canReanalyze,
    loadAnalysisReport,
    startNewAnalysis,
    startReanalysis,
    togglePauseAnalysis,
    selectChat,
    showAgentDetail,
    showReportView,
    retryLoad,
    initPage,
  }
}
