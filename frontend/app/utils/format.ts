/**
 * 格式化工具函数
 *
 * 提供时间、状态、评分等通用格式化功能
 * 所有函数均为纯函数，无 Vue 响应式依赖
 */

/* ========== 时间格式化 ========== */

/* 时间格式化缓存（LRU） */
const timeFormatCache = new Map<string, string>()
const TIME_CACHE_MAX = 200

/* 格式化时间 */
export function formatTime(dateStr: string): string {
  if (!dateStr) {
    return '未知时间'
  }

  /* LRU 缓存：相同日期字符串避免重复解析 */
  const cached = timeFormatCache.get(dateStr)
  if (cached !== undefined) return cached

  /* 后端返回的时间为UTC时间，如果字符串没有时区信息，追加'Z'标记为UTC */
  let normalizedStr = dateStr
  if (typeof normalizedStr === 'string'
    && !normalizedStr.endsWith('Z')
    && !/[+-]\d{2}:\d{2}$/.test(normalizedStr)) {
    normalizedStr = normalizedStr + 'Z'
  }

  const date = new Date(normalizedStr)

  /* 检查日期是否有效 */
  if (isNaN(date.getTime())) {
    return '未知时间'
  }

  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  let result: string
  if (days === 0) {
    result = `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else if (days === 1) {
    result = `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else {
    result = `${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  }

  /* 写入缓存 */
  if (timeFormatCache.size >= TIME_CACHE_MAX) {
    const firstKey = timeFormatCache.keys().next().value
    if (firstKey !== undefined) timeFormatCache.delete(firstKey)
  }
  timeFormatCache.set(dateStr, result)
  return result
}

/* ========== 持有期格式化 ========== */

/* 格式化持有期：数字时追加"天"，字符串时直接显示 */
export function formatHoldingPeriod(period: number | string | undefined): string {
  if (period === undefined || period === null || period === '') {
    return '暂无数据'
  }
  if (typeof period === 'number') {
    return `${period}天`
  }
  const numVal = Number(period)
  if (!isNaN(numVal) && period !== '暂不适用' && period !== '无法判断') {
    return `${numVal}天`
  }
  return String(period)
}

/* ========== 错误信息格式化 ========== */

/* 将原始错误信息转换为用户友好提示 */
export function getFriendlyErrorMessage(message: string): string {
  if (!message) return '分析过程中发生错误'
  /* 识别 LLM 配额耗尽错误 */
  if (message.includes('AllocationQuota') || message.includes('free tier') || message.includes('FreeTierOnly')) {
    return 'LLM 服务配额已耗尽，请联系管理员或更换 API Key'
  }
  /* 识别 LLM 权限错误 */
  if (message.includes('403') && message.includes('error')) {
    return 'LLM 服务权限不足，请联系管理员'
  }
  /* 识别限流错误 */
  if (message.includes('429') || message.includes('RateLimit')) {
    return 'LLM 服务请求过于频繁，请稍后重试'
  }
  /* 截断过长的错误信息 */
  if (message.length > 80) {
    return message.substring(0, 80) + '...'
  }
  return message
}

/* ========== 状态文本映射 ========== */

/* 获取智能体状态文本 */
export function getAgentStatusText(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '分析中',
    completed: '已完成',
    error: '出错'
  }
  return map[status] || '未知'
}

/* 获取工具状态文本 */
export function getToolStatusText(status?: string): string {
  const map: Record<string, string> = {
    pending: '调用中',
    success: '执行成功',
    failed: '执行失败',
    completed: '已完成'
  }
  return map[status || ''] || '未知'
}

/* 获取会话状态文本 */
export function getStatusText(chat: { status: string; decision: string; shortTermDecision?: string; longTermDecision?: string }): string {
  if (chat.status === 'running') return '分析中'
  if (chat.status === 'pending') return '待分析'
  if (chat.status === 'failed') return '失败'

  /* 已完成：显示带"建议"前缀的决策方向 */
  if (chat.status === 'completed') {
    const dir = chat.shortTermDecision || chat.decision || ''
    if (dir === 'buy' || dir === '买入') return '建议买入'
    if (dir === 'sell' || dir === '卖出') return '建议卖出'
    if (dir === 'hold' || dir === '持有') return '建议持有'
    return '已完成'
  }

  return chat.decision || '未知'
}

/* 获取会话状态样式类 */
export function getStatusClass(status: string): string {
  const classMap: Record<string, string> = {
    pending: 'status-pending',
    running: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed'
  }
  return classMap[status] || ''
}

/* 获取决策方向样式类（匹配报告中的颜色） */
export function getDecisionClass(chat: { status: string; decision: string; shortTermDecision?: string; longTermDecision?: string }): string {
  if (chat.status !== 'completed') return getStatusClass(chat.status)

  const dir = chat.shortTermDecision || chat.decision || ''
  if (dir === 'buy' || dir === '买入') return 'decision-buy'
  if (dir === 'sell' || dir === '卖出') return 'decision-sell'
  if (dir === 'hold' || dir === '持有') return 'decision-hold'
  return getStatusClass(chat.status)
}

/* ========== 评分格式化 ========== */

/* 格式化智能体评分 */
export function formatAgentScore(agent: { score?: number | string }): string {
  if (agent.score === undefined || agent.score === null) return ''
  if (typeof agent.score === 'number') {
    return `评分：${agent.score.toFixed(1)}`
  }
  return String(agent.score)
}
