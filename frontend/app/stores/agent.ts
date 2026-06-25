import { defineStore } from 'pinia'
import { ref, shallowRef, computed, triggerRef } from 'vue'
import { getToolChineseName, formatToolResult } from '~/utils/toolNameMap'

/* 智能体类型 */
export type AgentType = 'fundamental' | 'technical' | 'risk' | 'cost' | 'sentiment' | 'decision'

/* 智能体状态 */
export type AgentStatus = 'pending' | 'running' | 'completed' | 'error'

/* 智能体信息 */
export interface AgentInfo {
  type: AgentType
  name: string
  status: AgentStatus
  score?: number | string
  summary?: string
  thinking?: ThinkingStep[]
  result?: string
  startTime?: string
  endTime?: string
}

/* 思考过程步骤 */
export interface ThinkingStep {
  id: string
  time: string
  text: string
  type: 'status' | 'tool_call' | 'tool_result' | 'thinking' | 'deep_thinking'
  thinkingId?: string
  isStreaming?: boolean
  deepThinkingContent?: string
  isComplete?: boolean
  toolName?: string
  toolChineseName?: string
  toolArgs?: Record<string, any>
  toolStatus?: string
  toolResult?: Record<string, any>
  toolResultText?: string
}

/* 智能体状态 Store */
export const useAgentStore = defineStore('agent', () => {
  /* ========== State ========== */

  /* 各智能体状态 — shallowRef 避免 Map 深层响应式开销 */
  const agents = shallowRef<Map<AgentType, AgentInfo>>(new Map([
    ['fundamental', { type: 'fundamental', name: '基本面分析师', status: 'pending' }],
    ['technical', { type: 'technical', name: '技术分析师', status: 'pending' }],
    ['risk', { type: 'risk', name: '风险分析师', status: 'pending' }],
    ['cost', { type: 'cost', name: '成本分析师', status: 'pending' }],
    ['sentiment', { type: 'sentiment', name: '情绪分析师', status: 'pending' }],
    ['decision', { type: 'decision', name: '决策智能体', status: 'pending' }],
  ]))

  /* 思考过程记录 */
  const thinkingProcess = ref<ThinkingStep[]>([])

  /* 当前选中的智能体 */
  const currentAgentType = ref<AgentType>('fundamental')

  /* ========== Getters ========== */

  /* 已完成的智能体列表 */
  const completedAgents = computed(() => {
    const completed: AgentInfo[] = []
    agents.value.forEach((agent) => {
      if (agent.status === 'completed') {
        completed.push(agent)
      }
    })
    return completed
  })

  /* 是否所有智能体都已完成 */
  const allCompleted = computed(() => {
    let allDone = true
    agents.value.forEach((agent) => {
      if (agent.status !== 'completed') {
        allDone = false
      }
    })
    return allDone
  })

  /* 正在运行的智能体 */
  const runningAgents = computed(() => {
    const running: AgentInfo[] = []
    agents.value.forEach((agent) => {
      if (agent.status === 'running') {
        running.push(agent)
      }
    })
    return running
  })

  /* 获取当前智能体信息 */
  const currentAgent = computed(() => {
    return agents.value.get(currentAgentType.value) || null
  })

  /* 获取智能体列表（按顺序） */
  const agentList = computed(() => {
    const order: AgentType[] = ['fundamental', 'technical', 'risk', 'cost', 'sentiment', 'decision']
    return order.map(type => agents.value.get(type)).filter(Boolean) as AgentInfo[]
  })

  /* 完成进度 */
  const progress = computed(() => {
    const total = agents.value.size
    const completed = completedAgents.value.length
    return Math.round((completed / total) * 100)
  })

  /* ========== Actions ========== */

  /* 更新智能体状态 */
  function updateAgentStatus(
    type: AgentType,
    status: AgentStatus,
    data?: Partial<AgentInfo>
  ) {
    const agent = agents.value.get(type)
    if (!agent) return

    /* 防止回放事件导致已完成/失败的智能体状态回退到运行中 */
    if (status === 'running' && (agent.status === 'completed' || agent.status === 'error')) {
      return
    }

    // 过滤掉 undefined 值，避免覆盖已有数据
    const filteredData: Partial<AgentInfo> = {}
    if (data) {
      for (const [key, value] of Object.entries(data)) {
        if (value !== undefined) {
          (filteredData as any)[key] = value
        }
      }
    }
    // 创建新的 Map 实例以触发响应式更新
    const newMap = new Map(agents.value)
    newMap.set(type, {
      ...agent,
      status,
      ...filteredData,
    })
    agents.value = newMap
  }

  /* 设置智能体评分 */
  function setAgentScore(type: AgentType, score: number | string) {
    const agent = agents.value.get(type)
    if (agent) {
      const newMap = new Map(agents.value)
      newMap.set(type, {
        ...agent,
        score,
      })
      agents.value = newMap
    }
  }

  /* 设置智能体摘要 */
  function setAgentSummary(type: AgentType, summary: string) {
    const agent = agents.value.get(type)
    if (agent) {
      const newMap = new Map(agents.value)
      newMap.set(type, {
        ...agent,
        summary,
      })
      agents.value = newMap
    }
  }

  /* 添加思考步骤到指定智能体 */
  function addThinkingToAgent(type: AgentType, step: ThinkingStep) {
    const agent = agents.value.get(type)
    if (!agent) return

    /* 去重检查：如果已存在相同 thinkingId 的思考步骤，跳过添加 */
    if (step.thinkingId && agent.thinking) {
      const exists = agent.thinking.some(s => s.thinkingId === step.thinkingId)
      if (exists) return
    }

    const thinking = [...(agent.thinking || []), step]
    // 创建新的 Map 实例以触发响应式更新
    const newMap = new Map(agents.value)
    newMap.set(type, {
      ...agent,
      thinking,
    })
    agents.value = newMap
  }

  /* 设置智能体分析结果 */
  function setAgentResult(type: AgentType, result: string) {
    const agent = agents.value.get(type)
    if (agent) {
      const newMap = new Map(agents.value)
      newMap.set(type, {
        ...agent,
        result,
      })
      agents.value = newMap
    }
  }

  /* 添加思考过程（全局） */
  function addThinking(step: ThinkingStep) {
    thinkingProcess.value.push(step)
  }

  /* 批量添加思考过程 */
  function addThinkingBatch(steps: ThinkingStep[]) {
    thinkingProcess.value.push(...steps)
  }

  /* 清除思考过程 */
  function clearThinking() {
    thinkingProcess.value = []
  }

  /* 设置当前智能体 */
  function setCurrentAgent(type: AgentType) {
    currentAgentType.value = type
  }

  /* 重置所有智能体状态 */
  function resetAgents() {
    agents.value = new Map([
      ['fundamental', { type: 'fundamental', name: '基本面分析师', status: 'pending' }],
      ['technical', { type: 'technical', name: '技术分析师', status: 'pending' }],
      ['risk', { type: 'risk', name: '风险分析师', status: 'pending' }],
      ['cost', { type: 'cost', name: '成本分析师', status: 'pending' }],
      ['sentiment', { type: 'sentiment', name: '情绪分析师', status: 'pending' }],
      ['decision', { type: 'decision', name: '决策智能体', status: 'pending' }],
    ])
    thinkingProcess.value = []
    currentAgentType.value = 'fundamental'
  }

  /* 清除所有智能体状态 */
  function clearAgents() {
    resetAgents()
  }

  /* 添加流式思考内容到指定智能体，同一 thinkingId 的多条流式事件合并为一条记录 */
  function addStreamingThinking(
    type: AgentType,
    data: { thinkingId: string, content: string, thinkingType: string }
  ) {
    const agent = agents.value.get(type)
    if (!agent) return

    const { thinkingId, content, thinkingType } = data
    const existingThinking = agent.thinking || []

    /* 去重检查：如果该 thinkingId 对应的思考段已完成，跳过重复的流式事件 */
    const existingStep = existingThinking.find(s => s.thinkingId === thinkingId)
    if (existingStep && existingStep.isComplete) return

    /* 查找是否已存在该 thinkingId 的思考记录 */
    const existingIndex = existingThinking.findIndex(
      step => step.thinkingId === thinkingId
    )

    let updatedThinking: ThinkingStep[]

    if (existingIndex >= 0) {
      /* 如果已存在，追加内容到现有记录 */
      updatedThinking = [...existingThinking]
      const existingStep = updatedThinking[existingIndex]
      const isDeepThinking = thinkingType === 'deep_thinking'

      updatedThinking[existingIndex] = {
        ...existingStep,
        isStreaming: true,
        ...(isDeepThinking
          ? { deepThinkingContent: (existingStep.deepThinkingContent || '') + content }
          : { text: (existingStep.text || '') + content }
        ),
      }
    } else {
      /* 如果不存在，创建新的思考记录 */
      const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      const newStep: ThinkingStep = {
        id: `thinking-${thinkingId}-${Date.now()}`,
        time: now,
        text: thinkingType === 'deep_thinking' ? '' : content,
        type: thinkingType === 'deep_thinking' ? 'deep_thinking' : 'thinking',
        thinkingId,
        isStreaming: true,
        deepThinkingContent: thinkingType === 'deep_thinking' ? content : undefined,
        isComplete: false,
      }
      updatedThinking = [...existingThinking, newStep]
    }

    /* 创建新的 Map 实例以触发响应式更新 */
    const newMap = new Map(agents.value)
    newMap.set(type, {
      ...agent,
      thinking: updatedThinking,
    })
    agents.value = newMap
    triggerRef(agents)
  }

  /* 标记某段思考完成 */
  function completeThinking(type: AgentType, thinkingId: string) {
    const agent = agents.value.get(type)
    if (!agent) return

    const existingThinking = agent.thinking || []
    const updatedThinking = existingThinking.map(step => {
      if (step.thinkingId === thinkingId) {
        return {
          ...step,
          isStreaming: false,
          isComplete: true,
        }
      }
      return step
    })

    /* 创建新的 Map 实例以触发响应式更新 */
    const newMap = new Map(agents.value)
    newMap.set(type, {
      ...agent,
      thinking: updatedThinking,
    })
    agents.value = newMap
  }

  /* 添加工具调用记录到指定智能体 */
  function addToolCall(
    type: AgentType,
    data: { toolName: string, toolChineseName?: string, toolArgs: any, status: string, result?: any, resultText?: string }
  ) {
    const agent = agents.value.get(type)
    if (!agent) return

    /* 去重检查：如果已存在相同 toolName 和 toolArgs 的工具调用，跳过添加 */
    if (agent.thinking) {
      const argsKey = JSON.stringify(data.toolArgs)
      const exists = agent.thinking.some(
        s => s.type === 'tool_call' && s.toolName === data.toolName && JSON.stringify(s.toolArgs) === argsKey
      )
      if (exists) return
    }

    const { toolName, toolChineseName, toolArgs, status, result, resultText } = data
    const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    const displayName = toolChineseName || toolName

    const toolCallStep: ThinkingStep = {
      id: `tool-${toolName}-${Date.now()}`,
      time: now,
      text: `正在${displayName}...`,
      type: 'tool_call',
      toolName,
      toolChineseName: displayName,
      toolArgs,
      toolStatus: status,
      toolResult: result,
      toolResultText: resultText,
      isComplete: status === 'success' || status === 'completed' || status === 'failed',
    }

    const updatedThinking = [...(agent.thinking || []), toolCallStep]

    /* 创建新的 Map 实例以触发响应式更新 */
    const newMap = new Map(agents.value)
    newMap.set(type, {
      ...agent,
      thinking: updatedThinking,
    })
    agents.value = newMap
  }

  /* 处理 SSE 智能体更新消息 */
  function handleAgentUpdate(data: {
    type: AgentType
    status: AgentStatus
    score?: number | string
    summary?: string
    thinking?: ThinkingStep
    result?: string
  }) {
    const { type, status, score, summary, thinking, result } = data

    /* 更新智能体状态 */
    updateAgentStatus(type, status, {
      score,
      summary,
      result,
    })

    /* 添加思考步骤 */
    if (thinking) {
      addThinkingToAgent(type, thinking)
      addThinking(thinking)
    }
  }

  /* 从会话数据恢复智能体状态（页面重新加载时使用） */
  function restoreFromSessionData(agentOutputs: Array<{
    agentType: string
    status: string
    score?: number | null
    summary?: string | null
    thinkingProcess?: Array<Record<string, any>> | null
    toolsCalled?: Array<{
      name: string
      args: Record<string, any>
      result?: { success: boolean; data?: any; error?: string } | null
      time?: string
      timestamp?: string
    }> | null
  }>) {
    /* 在内存中一次性构建完整的智能体 Map，最后单次赋值减少响应式抖动 */
    const freshMap = new Map<AgentType, AgentInfo>([
      ['fundamental', { type: 'fundamental', name: '基本面分析师', status: 'pending' }],
      ['technical', { type: 'technical', name: '技术分析师', status: 'pending' }],
      ['risk', { type: 'risk', name: '风险分析师', status: 'pending' }],
      ['cost', { type: 'cost', name: '成本分析师', status: 'pending' }],
      ['sentiment', { type: 'sentiment', name: '情绪分析师', status: 'pending' }],
      ['decision', { type: 'decision', name: '决策智能体', status: 'pending' }],
    ])

    for (const output of agentOutputs) {
      const agentType = output.agentType as AgentType
      const agent = freshMap.get(agentType)
      if (!agent) continue

      const status = output.status === 'failed' ? 'error' : (output.status as AgentStatus)

      // ---- 1. 从 toolsCalled 重建 tool_call 类型步骤 ----
      const toolCallSteps: ThinkingStep[] = (output.toolsCalled || []).map((tc, idx) => {
        const chineseName = getToolChineseName(tc.name)
        const isSuccess = tc.result?.success ?? false
        // 转换时间戳为 HH:MM:SS 格式
        // 优先使用后端新增的 time 字段（与 thinking_process 同源），
        // 兼容旧数据的 timestamp 字段（ISO 字符串中提取）
        let timeStr = tc.time || ''
        if (!timeStr && tc.timestamp) {
          const match = tc.timestamp.match(/T(\d{2}:\d{2}:\d{2})/)
          timeStr = match ? match[1] : ''
        }
        const resultText = tc.result?.data ? formatToolResult(tc.name, tc.result.data) : ''
        return {
          id: `tool-restored-${tc.name}-${Date.now()}-${idx}`,
          time: timeStr,
          text: `正在${chineseName}...`,
          type: 'tool_call' as const,
          toolName: tc.name,
          toolChineseName: chineseName,
          toolArgs: tc.args,
          toolStatus: isSuccess ? 'success' : 'failed',
          toolResult: tc.result as Record<string, any>,
          toolResultText: resultText,
          isComplete: true,
          isStreaming: false,
        }
      })

      // ---- 2. 从 thinkingProcess 重建普通/深度思考步骤 ----
      // 过滤掉与工具调用对应的 "xxx完成"/"xxx失败" 文本，避免重复
      const toolCompletionTexts = new Set<string>()
      for (const tc of toolCallSteps) {
        const cnName = tc.toolChineseName || ''
        if (cnName) {
          toolCompletionTexts.add(`${cnName}完成`)
          // "xxx失败" 可能带错误信息后缀，用 startsWith 匹配
        }
      }

      const thinkingFromProcess: ThinkingStep[] | undefined = output.thinkingProcess && output.thinkingProcess.length > 0
        ? output.thinkingProcess
            .filter((item: any) => {
              const text = (item.text || '').trim()
              if (!text) return true
              // 跳过工具调用完成消息
              if (toolCompletionTexts.has(text)) return false
              for (const prefix of toolCompletionTexts) {
                if (prefix.endsWith('完成') && text === prefix) return false
                if (text.startsWith(prefix.replace('完成', '失败'))) return false
              }
              return true
            })
            .map((item: any, idx: number) => {
              const thinkingId = item.thinkingId || item.thinking_id || `restored-${Date.now()}-${idx}`
              let stepType: ThinkingStep['type'] = 'thinking'
              /* thinkingType (camelCase) 来自 API transformKeys 转换，thinking_type 作为后备 */
              const rawType = item.thinkingType || item.thinking_type || item.type || ''
              if (rawType === 'deep_thinking') {
                stepType = 'deep_thinking'
              } else if (rawType === 'status') {
                stepType = 'status'
              }
              return {
                id: thinkingId,
                time: item.time || '',
                text: item.text || '',
                type: stepType,
                thinkingId,
                isComplete: true,
                deepThinkingContent: stepType === 'deep_thinking' ? item.text : undefined,
                isStreaming: false,
              }
            })
        : undefined

      // ---- 3. 合并所有步骤并按时间排序 ----
      const allSteps = [...toolCallSteps, ...(thinkingFromProcess || [])]
      allSteps.sort((a, b) => a.time.localeCompare(b.time))
      const thinking = allSteps.length > 0 ? allSteps : undefined

      // 从 summary 恢复分析结果
      const result = output.summary || undefined

      // 在内存 Map 中设置，不触发响应式
      freshMap.set(agentType, {
        ...agent,
        status,
        score: output.score ?? undefined,
        summary: output.summary || undefined,
        thinking,
        result,
      })
    }

    /* 单次响应式赋值：1次触发代替原来的 N 次 */
    agents.value = freshMap
    thinkingProcess.value = []
    currentAgentType.value = 'fundamental'
  }

  return {
    /* State */
    agents,
    thinkingProcess,
    currentAgentType,

    /* Getters */
    completedAgents,
    allCompleted,
    runningAgents,
    currentAgent,
    agentList,
    progress,

    /* Actions */
    updateAgentStatus,
    setAgentScore,
    setAgentSummary,
    addThinkingToAgent,
    addStreamingThinking,
    completeThinking,
    addToolCall,
    setAgentResult,
    addThinking,
    addThinkingBatch,
    clearThinking,
    setCurrentAgent,
    resetAgents,
    clearAgents,
    handleAgentUpdate,
    restoreFromSessionData,
  }
})

/* 导出类型 */
export type AgentStore = ReturnType<typeof useAgentStore>
