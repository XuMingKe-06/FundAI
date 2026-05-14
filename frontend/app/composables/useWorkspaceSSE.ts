/**
 * 工作台 SSE 流式事件处理组合式函数
 *
 * 封装 SSE 连接管理、事件注册和数据处理逻辑
 * 依赖外部回调函数处理跨模块交互
 */

import { useAgentStore, type AgentType } from '~/stores/agent'
import { useAnalysisStore } from '~/stores/analysis'
import { useSessionStore } from '~/stores/session'
import { useSSE } from '~/composables/useSSE'
import { getToolChineseName, formatToolResult, replaceToolNameInText } from '~/utils/toolNameMap'
import { getFriendlyErrorMessage } from '~/utils/format'
import type { Ref } from 'vue'

/* SSE 组合式函数的配置选项 */
export interface UseWorkspaceSSEOptions {
  currentView: Ref<'report' | 'agent'>
  hasAutoSelectedAgent: Ref<boolean>
}

export function useWorkspaceSSE(options: UseWorkspaceSSEOptions) {
  const { currentView, hasAutoSelectedAgent } = options

  const agentStore = useAgentStore()
  const analysisStore = useAnalysisStore()
  const sessionStore = useSessionStore()
  const { connect: connectSSE, disconnect: disconnectSSE, on: onSSEEvent, markStreamEnded } = useSSE()

  /* 连接分析流（无需认证 token） */
  function connectToAnalysisStream(sessionId: string) {
    const baseUrl = '/api/v1'
    const streamUrl = `${baseUrl}/analysis/sessions/${sessionId}/stream`
    connectSSE(streamUrl)
  }

  /* 注册 SSE 事件处理器（loadAnalysisReport 由外部传入，避免循环依赖） */
  function setupSSEHandlers(loadAnalysisReport: (sessionId: string) => Promise<void>) {
    /* 处理智能体快照事件（页面刷新重连时接收已有智能体状态） */
    onSSEEvent('agent_snapshot', (data: any) => {
      if (!data || !data.agent_type) return
      const agentType = data.agent_type as AgentType
      const status = data.status === 'failed' || data.status === 'error' ? 'error' : data.status
      /* 检查智能体是否已有思考数据（来自 restoreFromSessionData），避免重复恢复 */
      const existingAgent = agentStore.agents.get(agentType)
      const alreadyHasThinking = !!(existingAgent && existingAgent.thinking && existingAgent.thinking.length > 0)
      /* 用快照数据直接设置智能体状态 */
      agentStore.handleAgentUpdate({
        type: agentType,
        status,
        score: data.score,
        summary: data.summary,
      })
      if (data.result) {
        agentStore.setAgentResult(agentType, typeof data.result === 'string' ? data.result : JSON.stringify(data.result))
      }
      /* 仅在智能体尚未恢复思考数据时，从快照恢复思考过程和工具调用 */
      if (!alreadyHasThinking) {
        if (data.thinking_process && Array.isArray(data.thinking_process)) {
          data.thinking_process.forEach((item: any) => {
            let stepType: 'thinking' | 'deep_thinking' | 'status' = 'thinking'
            const rawType = item.thinking_type || item.type || ''
            if (rawType === 'deep_thinking') stepType = 'deep_thinking'
            else if (rawType === 'status') stepType = 'status'
            agentStore.addThinkingToAgent(agentType, {
              id: item.thinking_id || `snapshot-${Date.now()}-${Math.random()}`,
              time: item.time || '',
              text: item.text || '',
              type: stepType,
              thinkingId: item.thinking_id,
              isComplete: true,
              deepThinkingContent: stepType === 'deep_thinking' ? item.text : undefined,
              isStreaming: false,
            })
          })
        }
        if (data.tools_called && Array.isArray(data.tools_called)) {
          data.tools_called.forEach((tc: any) => {
            const chineseName = getToolChineseName(tc.name)
            const resultText = tc.result?.data ? formatToolResult(tc.name, tc.result.data) : ''
            agentStore.addToolCall(agentType, {
              toolName: tc.name,
              toolChineseName: chineseName,
              toolArgs: tc.args,
              status: tc.result?.success ? 'success' : 'failed',
              result: tc.result,
              resultText,
            })
          })
        }
      }
    })

    /* 处理智能体状态更新事件 */
    onSSEEvent('agent_status', (data: any) => {
      const updateData: any = {
        type: data.agent_type as AgentType,
        status: data.status,
      }
      if (data.score !== undefined && data.score !== null) {
        updateData.score = data.score
      }
      if (data.summary !== undefined && data.summary !== null) {
        updateData.summary = data.summary
      }
      agentStore.handleAgentUpdate(updateData)

      /* 当第一个智能体开始运行时，自动选中并切换到 agent 视图 */
      if (data.status === 'running' && !hasAutoSelectedAgent.value) {
        hasAutoSelectedAgent.value = true
        agentStore.setCurrentAgent(data.agent_type as AgentType)
        currentView.value = 'agent'
      }

      /* 更新左侧栏会话状态 */
      const currentSessionId = sessionStore.currentSession?.id
      if (currentSessionId) {
        const session = sessionStore.sessions.find(s => s.id === currentSessionId)
        if (session) {
          if (data.status === 'running' && (session.status === 'pending' || session.status === 'running')) {
            session.status = 'running'
            session.decision = '分析中'
          }
        }
      }
    })

    /* 处理思考过程事件 */
    onSSEEvent('thinking', (data: any) => {
      /* 将UTC时间戳转换为本地时间显示 */
      let timeStr = ''
      if (data.timestamp) {
        const date = new Date(data.timestamp)
        if (!isNaN(date.getTime())) {
          timeStr = date.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }
      }
      if (!timeStr && data.time) {
        timeStr = data.time
      }
      if (!timeStr) {
        timeStr = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }
      /* 将思考文本中的英文工具名替换为中文名 */
      const rawText = data.text || data.content || ''
      const displayText = replaceToolNameInText(rawText)
      const thinkingData = {
        id: data.thinking_id || `thinking-${Date.now()}`,
        type: 'thinking' as const,
        thinkingId: data.thinking_id,
        time: timeStr,
        text: displayText,
        thinking_type: data.thinking_type || 'normal'
      }
      agentStore.addThinkingToAgent(data.agent_type as AgentType, thinkingData)
      agentStore.addThinking(thinkingData)
    })

    /* 处理LLM流式思考内容事件 */
    onSSEEvent('llm_thinking_stream', (data: any) => {
      if (!data || !data.agent_type || !data.thinking_id) return

      const agentType = data.agent_type as AgentType
      const thinkingId = data.thinking_id
      const content = data.content || ''
      const thinkingType = data.thinking_type || 'normal'
      const isComplete = data.is_complete || false

      /* 去重检查：如果该思考段已完成，跳过重连回放的重复事件 */
      const existingAgent = agentStore.agents.get(agentType)
      if (existingAgent && existingAgent.thinking) {
        const existingStep = existingAgent.thinking.find(s => s.thinkingId === thinkingId)
        if (existingStep && existingStep.isComplete) return
      }

      /* 追加流式思考内容 */
      agentStore.addStreamingThinking(agentType, {
        thinkingId,
        content,
        thinkingType
      })

      /* 如果标记为完成，标记思考完成 */
      if (isComplete) {
        agentStore.completeThinking(agentType, thinkingId)
      }
    })

    /* 处理工具调用事件 */
    onSSEEvent('tool_call', (data: any) => {
      if (!data || !data.agent_type || !data.tool_name) return

      const agentType = data.agent_type as AgentType
      const toolName = data.tool_name
      const chineseName = getToolChineseName(toolName)
      const status = data.status || 'pending'

      /* 格式化工具结果 */
      let resultText = ''
      if (data.result && data.result.success && data.result.data) {
        resultText = formatToolResult(toolName, data.result.data)
      }

      agentStore.addToolCall(agentType, {
        toolName,
        toolChineseName: chineseName,
        toolArgs: data.tool_args,
        status,
        result: data.result,
        resultText,
      })
    })

    /* 处理智能体完成事件 */
    onSSEEvent('agent_complete', (data: any) => {
      if (!data || !data.agent_type) {
        console.warn('[SSE] 收到不完整的智能体完成事件')
        return
      }
      const agentStatus = data.status === 'failed' ? 'error' : 'completed'
      const updateData: any = {
        type: data.agent_type as AgentType,
        status: agentStatus,
      }
      if (data.score !== undefined && data.score !== null) {
        updateData.score = data.score
      }
      if (data.summary !== undefined && data.summary !== null) {
        /* 对失败的智能体，友好化摘要信息 */
        updateData.summary = data.status === 'failed' ? getFriendlyErrorMessage(data.summary) : data.summary
      }
      if (data.result !== undefined && data.result !== null) {
        updateData.result = typeof data.result === 'string' ? data.result : (data.result.summary || JSON.stringify(data.result, null, 2))
      } else if (data.summary !== undefined && data.summary !== null) {
        updateData.result = data.status === 'failed' ? getFriendlyErrorMessage(data.summary) : data.summary
      }
      /* 决策智能体失败时，将错误信息作为summary展示 */
      if (data.status === 'failed' && data.agent_type === 'decision' && !data.summary) {
        updateData.summary = '决策分析失败'
      }
      agentStore.handleAgentUpdate(updateData)
    })

    /* 处理智能体结果事件 */
    onSSEEvent('result', (data: any) => {
      if (!data || !data.agent_type) return
      const agentType = data.agent_type as AgentType
      const result = data.result
      if (result !== undefined && result !== null) {
        let resultStr: string
        if (typeof result === 'string') {
          resultStr = result
        } else if (result.summary) {
          resultStr = result.summary
        } else {
          resultStr = JSON.stringify(result, null, 2)
        }
        agentStore.setAgentResult(agentType, resultStr)
      }
    })

    /* 处理分析完成事件 */
    onSSEEvent('analysis_complete', (data: any) => {
      /* 自动切换回报告视图 */
      currentView.value = 'report'

      /* 重置暂停状态 */
      analysisStore.isPaused = false
      analysisStore.clearPauseState()

      if (data.report) {
        analysisStore.currentReport = data.report
        analysisStore.progress = 100
      }

      /* 更新左侧栏会话状态为已完成 */
      const currentSessionId = sessionStore.currentSession?.id
      if (currentSessionId) {
        const session = sessionStore.sessions.find(s => s.id === currentSessionId)
        if (session) {
          session.status = 'completed'
          session.decision = '已完成'
        }
        /* 加载报告，完成后更新决策方向 */
        loadAnalysisReport(currentSessionId).then(() => {
          if (session && analysisStore.currentReport?.decision?.shortTerm?.direction) {
            const d = analysisStore.currentReport.decision.shortTerm.direction
            session.shortTermDecision = d
            session.longTermDecision = analysisStore.currentReport.decision.longTerm?.direction
            session.decision = d
          }
        })
      }

      /* 标记 SSE 流正常结束，防止重连 */
      markStreamEnded()

      /* 断开 SSE 连接 */
      disconnectSSE()

      /* 刷新会话列表 */
      sessionStore.fetchSessions()
    })

    /* 处理错误事件 */
    onSSEEvent('error', (data: any) => {
      /* 数据校验：确保 data 存在 */
      if (!data) {
        console.warn('[SSE] 收到空错误事件数据')
        return
      }

      /*
       * 区分两类错误：
       * 1) 后端分析错误（有 agent_type）— 真正的分析异常
       * 2) 连接层错误（无 agent_type）— 网络/代理问题，由 useSSE 自动重连
       */
      if (!data.agent_type) {
        /* 连接层错误：不触发 store 状态变更，让 useSSE 的重连逻辑自行处理 */
        return
      }

      /* 友好化错误信息 */
      const rawMessage = data.message || '分析过程中发生错误'
      const friendlyMessage = getFriendlyErrorMessage(rawMessage)

      /* 如果是决策智能体的错误，更新决策智能体状态 */
      if (data.agent_type === 'decision') {
        agentStore.handleAgentUpdate({
          type: 'decision' as AgentType,
          status: 'error',
          summary: friendlyMessage,
        })
      }

      analysisStore.error = friendlyMessage

      /* 更新左侧栏会话状态为失败 */
      const currentSessionId = sessionStore.currentSession?.id
      if (currentSessionId) {
        const session = sessionStore.sessions.find(s => s.id === currentSessionId)
        if (session) {
          session.status = 'failed'
          session.decision = '失败'
        }
      }

      /* 如果是决策智能体失败，不立即断开SSE，让后续的降级报告保存流程继续 */
      if (data.agent_type !== 'decision') {
        markStreamEnded()
        disconnectSSE()
      }
    })
  }

  return {
    connectToAnalysisStream,
    disconnectSSE,
    markStreamEnded,
    setupSSEHandlers,
  }
}
