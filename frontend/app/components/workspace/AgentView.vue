<template>
  <div class="agent-workflow-container">
    <div class="agent-workflow-scroll">
      <!-- 工作流顶部状态栏 -->
      <div class="workflow-status-bar">
        <div class="workflow-title-group">
          <div class="workflow-title">
            多智能体协同分析
            <span v-if="fundCode" class="fund-code-highlight">{{ fundCode }}</span>
          </div>
          <div class="workflow-subtitle">
            <template v-if="fundName">{{ fundName }}</template>
            <template v-if="analysisMode"> | 分析模式: {{ analysisMode }}</template>
            <template v-if="riskPreference"> | 风险偏好: {{ riskPreference }}</template>
          </div>
        </div>
        <div v-if="isAnalyzing || hasAnyCompleted" class="workflow-progress-group">
          <span class="workflow-progress-text">{{ progress }}%</span>
          <div class="workflow-progress-bar">
            <div class="workflow-progress-fill" :style="{ width: `${progress}%` }"></div>
          </div>
          <span v-if="elapsedTime" class="workflow-elapsed">{{ elapsedTime }}</span>
        </div>
      </div>

      <!-- 工作流时间线 -->
      <div class="workflow-timeline">
        <template v-for="(agent, index) in agents" :key="agent.type">
          <!-- 辩论指示器：当相邻两个已完成智能体评分差异超过阈值时显示 -->
          <div
            v-if="shouldShowDebate(index)"
            class="debate-indicator"
          >
            <div class="debate-icon">!</div>
            <div>
              <div class="debate-text">评分分歧检测 - 触发辩论机制</div>
              <div class="debate-detail">
                {{ agents[index - 1].name }}({{ agents[index - 1].score }})与{{ agent.name }}({{ agent.score }})评分差异达{{ Math.abs((agents[index - 1].score || 0) - (agent.score || 0)) }}分，超过阈值，双方进入辩论调分环节
              </div>
            </div>
          </div>

          <!-- 智能体阶段节点 -->
          <div
            class="agent-phase"
            :class="[agent.status, { 'collapsed': isCollapsed(agent.type), 'decision-phase': agent.type === 'decision', 'focused': agent.type === focusedAgentType }]"
            :data-agent-type="agent.type"
          >
            <!-- 阶段圆点 -->
            <div class="phase-dot" :class="agent.status">
              <!-- 已完成：勾选图标 -->
              <svg v-if="agent.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <!-- 运行中：旋转图标 -->
              <svg v-else-if="agent.status === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/></svg>
              <!-- 出错：感叹号 -->
              <svg v-else-if="agent.status === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <!-- 等待中：智能体类型图标 -->
              <template v-else>
                <svg v-if="agent.type === 'fundamental'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/></svg>
                <svg v-else-if="agent.type === 'technical'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                <svg v-else-if="agent.type === 'risk'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <svg v-else-if="agent.type === 'cost'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                <svg v-else-if="agent.type === 'sentiment'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              </template>
            </div>

            <!-- 阶段卡片 -->
            <div class="phase-card">
              <!-- 阶段头部 -->
              <div class="phase-header" @click="toggleCollapse(agent.type)">
                <!-- 智能体图标 -->
                <div class="agent-icon" :class="agent.type">
                  <svg v-if="agent.type === 'fundamental'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/></svg>
                  <svg v-else-if="agent.type === 'technical'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  <svg v-else-if="agent.type === 'risk'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  <svg v-else-if="agent.type === 'cost'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                  <svg v-else-if="agent.type === 'sentiment'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
                <!-- 阶段信息 -->
                <div class="phase-info">
                  <div class="phase-name">{{ agent.name }}</div>
                  <div class="phase-desc">{{ getAgentDescription(agent.type) }}</div>
                </div>
                <!-- 评分徽章 -->
                <span v-if="agent.score != null && agent.status === 'completed'" class="phase-score">{{ agent.score }}</span>
                <!-- 状态徽章 -->
                <span class="phase-badge" :class="agent.status">{{ getAgentStatusText(agent.status) }}</span>
                <!-- 折叠按钮 -->
                <span class="phase-toggle">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                </span>
              </div>

              <!-- 阶段内容体 -->
              <div class="phase-body">
                <div class="phase-steps">
                  <template v-for="(step, stepIndex) in agent.thinking" :key="step.id || `step-${stepIndex}`">
                    <!-- 状态提示步骤 -->
                    <div v-if="step.type === 'status' && step.text?.trim()" class="step-row">
                      <span class="step-dot status"></span>
                      <div class="step-content">
                        <div class="step-label status">状态</div>
                        <div class="step-text">{{ step.text }}</div>
                      </div>
                    </div>

                    <!-- 普通思考步骤 -->
                    <div v-else-if="step.type === 'thinking' && step.text?.trim()" class="step-row">
                      <span class="step-dot thinking"></span>
                      <div class="step-content">
                        <div class="step-label thinking">思考</div>
                        <div class="step-text thinking-text md-content md-thinking" v-html="renderMarkdown(step.text)"></div>
                      </div>
                    </div>

                    <!-- 深度思考步骤 -->
                    <div v-else-if="step.type === 'deep_thinking'" class="step-row">
                      <span class="step-dot deep-thinking"></span>
                      <div class="step-content">
                        <div class="step-label deep-thinking">深度推理</div>
                        <div
                          class="deep-thinking-block"
                          :class="{ open: step.isStreaming || deepThinkingOpenMap[step.id || String(stepIndex)] }"
                          @click="toggleDeepThinking(step.id || String(stepIndex))"
                        >
                          <div class="deep-thinking-summary">
                            <span class="toggle-arrow">&#9654;</span>
                            Thinking... <template v-if="!step.isStreaming && !deepThinkingOpenMap[step.id || String(stepIndex)]">(点击展开)</template>
                            <template v-if="!step.isStreaming && deepThinkingOpenMap[step.id || String(stepIndex)]">(点击收起)</template>
                          </div>
                          <div v-if="step.isStreaming || deepThinkingOpenMap[step.id || String(stepIndex)]" class="deep-thinking-detail md-content md-thinking" v-html="renderMarkdown(step.deepThinkingContent || step.text)">
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 工具调用步骤 -->
                    <div v-else-if="step.type === 'tool_call'" class="step-row">
                      <span class="step-dot tool"></span>
                      <div class="step-content">
                        <div class="step-label tool">工具调用</div>
                        <div class="tool-call-block">
                          <div class="tool-call-header">
                            <span class="tool-badge">TOOL</span>
                            <span class="tool-name">{{ step.toolChineseName || step.toolName || step.text }}</span>
                            <span class="tool-status-badge" :class="getToolStatusClass(step.toolStatus)">{{ getToolStatusText(step.toolStatus) }}</span>
                          </div>
                          <div v-if="step.toolArgs" class="tool-call-args">{{ formatToolArgs(step.toolArgs) }}</div>
                        </div>
                        <!-- 工具结果展示 -->
                        <div v-if="step.toolResultText" class="tool-result-display">
                          <span class="tool-result-label">结果：</span>
                          <span class="tool-result-value">{{ step.toolResultText }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- 兼容旧格式数据（没有 type 字段但有文本内容） -->
                    <div v-else-if="(!step.type || step.type === 'legacy') && step.text?.trim()" class="step-row">
                      <span class="step-dot thinking"></span>
                      <div class="step-content">
                        <div class="step-label thinking">思考</div>
                        <div class="step-text thinking-text md-content md-thinking" v-html="renderMarkdown(step.text)"></div>
                      </div>
                    </div>
                  </template>

                  <!-- 思考指示器（运行中） -->
                  <div v-if="agent.status === 'running' && !isPaused" class="step-row">
                    <span class="step-dot thinking"></span>
                    <div class="step-content">
                      <div class="thinking-dots-indicator">
                        <div class="thinking-dots">
                          <span></span><span></span><span></span>
                        </div>
                        <span class="thinking-dots-label">正在思考...</span>
                      </div>
                    </div>
                  </div>

                  <!-- 暂停指示器 -->
                  <div v-if="agent.status === 'running' && isPaused" class="step-row">
                    <span class="step-dot" style="background: var(--color-warning-500)"></span>
                    <div class="step-content">
                      <div class="paused-indicator">
                        <span class="paused-label">PAUSED</span>
                      </div>
                    </div>
                  </div>

                  <!-- 分析结果摘要 -->
                  <div v-if="agent.result && agent.status === 'completed'" class="step-row">
                    <span class="step-dot result"></span>
                    <div class="step-content">
                      <div class="step-label result">分析完成</div>
                      <div class="result-summary">
                        <h4 v-if="agent.score != null">{{ agent.name }}评分: {{ agent.score }}/100</h4>
                        <div class="md-content" v-html="renderMarkdown(agent.result)"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智能体工作流时间线视图
 *
 * 以专业时间线布局展示所有智能体的运行状态和思考过程，
 * 每个智能体作为独立的阶段节点，支持折叠/展开。
 */

import { reactive, computed, watch, nextTick } from 'vue'
import { getAgentStatusText, getToolStatusText } from '~/utils/format'
import { renderMarkdown } from '~/utils/markdown'
import type { AgentInfo, AgentType } from '~/stores/agent'

/* ========== Props ========== */
const props = defineProps<{
  /* 所有智能体列表 */
  agents: AgentInfo[]
  /* 基金代码 */
  fundCode?: string
  /* 基金名称 */
  fundName?: string
  /* 分析模式 */
  analysisMode?: string
  /* 风险偏好 */
  riskPreference?: string
  /* 是否正在分析 */
  isAnalyzing: boolean
  /* 分析是否暂停 */
  isPaused: boolean
  /* 分析进度百分比 */
  progress: number
  /* 已用时间 */
  elapsedTime?: string
  /* 聚焦的智能体类型（从右侧栏点击时传入） */
  focusedAgentType?: AgentType
}>()

/* ========== 智能体描述映射 ========== */
const agentDescriptions: Record<string, string> = {
  fundamental: '基金持仓、经理能力、公司运营等基本面因素评估',
  technical: '净值走势、技术指标、趋势与动量分析',
  risk: '波动率、最大回撤、风险等级评估',
  cost: '申购赎回费率、管理费、托管费等成本评估',
  sentiment: '市场情绪、舆论倾向、资金流向分析',
  decision: '汇总所有分析结果，生成投资建议',
}

/* ========== 折叠状态管理 ========== */
/* 记录用户显式设置的展开/折叠状态，覆盖默认行为 */
const phaseExplicitStates = reactive<Record<string, 'collapsed' | 'expanded'>>({})

/* 深度思考块展开状态 */
const deepThinkingOpenMap = reactive<Record<string, boolean>>({})

/* 判断阶段是否折叠 */
function isCollapsed(type: string): boolean {
  const agent = props.agents.find(a => a.type === type)
  if (!agent) return false
  /* 用户显式设置优先 */
  const explicitState = phaseExplicitStates[type]
  if (explicitState === 'collapsed') return true
  if (explicitState === 'expanded') return false
  /* 默认：已完成的阶段折叠，运行中的展开 */
  return agent.status === 'completed'
}

/* 切换折叠状态 */
function toggleCollapse(type: string) {
  const currentlyCollapsed = isCollapsed(type)
  if (currentlyCollapsed) {
    phaseExplicitStates[type] = 'expanded'
  } else {
    phaseExplicitStates[type] = 'collapsed'
  }
}

/* 切换深度思考块展开状态 */
function toggleDeepThinking(key: string) {
  deepThinkingOpenMap[key] = !deepThinkingOpenMap[key]
}

/* ========== 辅助函数 ========== */

/* 获取智能体描述 */
function getAgentDescription(type: string): string {
  return agentDescriptions[type] || '智能体分析'
}

/* 获取工具状态CSS类名 */
function getToolStatusClass(status?: string): string {
  const map: Record<string, string> = {
    pending: 'running',
    success: 'success',
    failed: 'failed',
    completed: 'success',
  }
  return map[status || ''] || 'pending'
}

/* 格式化工具参数 */
function formatToolArgs(args: string | Record<string, any> | undefined): string {
  if (!args) return ''
  if (typeof args === 'string') return args
  try {
    return JSON.stringify(args, null, 2)
  } catch {
    return String(args)
  }
}

/* 判断是否显示辩论指示器 */
function shouldShowDebate(index: number): boolean {
  if (index === 0) return false
  const prev = props.agents[index - 1]
  const curr = props.agents[index]
  /* 两个相邻智能体都已完成，且评分差异超过15分 */
  if (prev.status !== 'completed' || curr.status !== 'completed') return false
  if (prev.score == null || curr.score == null) return false
  return Math.abs(Number(prev.score) - Number(curr.score)) > 15
}

/* 是否有任何智能体已完成 */
const hasAnyCompleted = computed(() => {
  return props.agents.some(a => a.status === 'completed')
})

/* ========== 聚焦智能体：自动展开并滚动 ========== */

/* 监听 focusedAgentType 变化，展开对应智能体并滚动到视口 */
watch(() => props.focusedAgentType, (newType) => {
  if (!newType) return

  /* 强制展开该智能体的工作流 */
  phaseExplicitStates[newType] = 'expanded'

  /* 等待 DOM 更新后滚动到对应智能体 */
  nextTick(() => {
    const targetEl = document.querySelector(`[data-agent-type="${newType}"]`)
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
}, { immediate: true })
</script>
