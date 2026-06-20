<template>
  <div class="workspace-page">
    <!-- 顶部导航栏 -->
    <WorkspaceHeader
      :fund-input="headerFundInput"
      :is-analyzing="isAnalyzing"
      :current-fund-code="currentFundCode"
      :current-fund-name="currentFundName"
      @update:fund-input="headerFundInput = $event"
      @start-analysis="startNewAnalysis"
    />

    <!-- 主内容区域 - 三栏布局 -->
    <div class="workspace-container">
      <!-- 左侧对话导航栏 -->
      <WorkspaceSidebarLeft
        :search="sidebarSearch"
        :sessions="sessionStore.sessions"
        :current-session-id="sessionStore.currentSession?.id"
        :loading="sessionStore.loading"
        :has-sessions="sessionStore.hasSessions"
        :context-menu-visible="contextMenuVisible"
        :context-menu-x="contextMenuX"
        :context-menu-y="contextMenuY"
        :collapsed="leftSidebarCollapsed"
        @update:search="sidebarSearch = $event"
        @select-session="selectChat"
        @right-click="handleRightClick"
        @delete-session="confirmDeleteSession"
        @toggle-collapse="leftSidebarCollapsed = !leftSidebarCollapsed"
      />

      <!-- 中间主内容区 -->
      <main class="main-content" :class="{ 'left-expanded': !leftSidebarCollapsed, 'right-expanded': !rightSidebarCollapsed }">
        <!-- 多标签页栏 -->
        <WorkspaceTabBar
          v-if="openTabs.length > 0"
          :tabs="openTabs"
          :active-tab-id="activeTabId"
          @select="switchTab"
          @close="closeTab"
        />

        <!-- 加载状态 - 仅在报告视图时显示 -->
        <div v-if="analysisStore.loading && !analysisStore.hasReport && currentView === 'report'" class="loading-container">
          <div class="loading-spinner"></div>
          <p>正在加载分析报告...</p>
        </div>

        <!-- 错误状态 - 仅在报告视图时显示 -->
        <div v-else-if="analysisStore.error && currentView === 'report'" class="error-container">
          <div class="error-icon">!</div>
          <h3>加载失败</h3>
          <p>{{ analysisStore.error }}</p>
          <button class="btn-retry" @click="retryLoad">{{ sessionStore.currentSession?.status === 'failed' ? '重新分析' : '重试' }}</button>
        </div>

        <!-- 空状态 - 仅在报告视图时显示 -->
        <div v-else-if="!analysisStore.hasReport && currentView === 'report' && !isAnalyzing" class="empty-container">
          <h3>开始分析基金</h3>
          <p>在顶部搜索框输入基金代码或名称，点击分析按钮开始</p>
        </div>

        <!-- 工作流时间线视图（分析中或查看智能体详情时显示） -->
        <WorkspaceAgentView
          v-else-if="isAnalyzing || currentView === 'agent'"
          :agents="agentList"
          :fund-code="currentFundCode"
          :fund-name="currentFundName"
          :analysis-mode="analysisModeLabel"
          :risk-preference="riskPreferenceLabel"
          :is-analyzing="isAnalyzing"
          :is-paused="analysisStore.isPaused"
          :progress="agentStore.progress"
          :elapsed-time="elapsedTime"
          :focused-agent-type="agentStore.currentAgentType"
        />

        <!-- 报告视图 -->
        <WorkspaceReportView
          v-else-if="currentView === 'report'"
          :report="currentReport"
        />
      </main>

      <!-- 右侧智能体进度栏 -->
      <WorkspaceSidebarRight
        :agent-list="agentList"
        :is-analyzing="isAnalyzing"
        :can-reanalyze="canReanalyze"
        :is-paused="analysisStore.isPaused"
        :collapsed="rightSidebarCollapsed"
        @reanalyze="startReanalysis"
        @toggle-pause="togglePauseAnalysis"
        @show-report="showReportView"
        @show-agent-detail="showAgentDetail"
        @toggle-collapse="rightSidebarCollapsed = !rightSidebarCollapsed"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 工作台页面
 *
 * 重构后的主文件仅负责布局编排和组合式函数的连接，
 * 业务逻辑分散至各 composable，UI 分散至各子组件
 */

import { useWorkspaceSSE } from '~/composables/useWorkspaceSSE'
import { useWorkspaceAnalysis } from '~/composables/useWorkspaceAnalysis'
import { useWorkspaceContextMenu } from '~/composables/useWorkspaceContextMenu'
import { useAnalysisSettings } from '~/composables/useAnalysisSettings'
import { useAgentStore } from '~/stores/agent'
import { useAnalysisStore } from '~/stores/analysis'
import { useSessionStore } from '~/stores/session'

/* ========== Store 初始化 ========== */
const agentStore = useAgentStore()
const analysisStore = useAnalysisStore()
const sessionStore = useSessionStore()
const { analysisMode } = useAnalysisSettings()

/* ========== 共享状态（跨组合式函数共享） ========== */
const currentView = ref<'report' | 'agent'>('report')
const hasAutoSelectedAgent = ref(false)
const headerFundInput = ref('')
const sidebarSearch = ref('')
const leftSidebarCollapsed = ref(false)
const rightSidebarCollapsed = ref(false)

/* ========== 多标签页管理 ========== */
interface TabInfo {
  id: string
  fundCode: string
  fundName: string
  direction?: 'buy' | 'sell' | 'hold'
}

const openTabs = ref<TabInfo[]>([])
const activeTabId = ref<string>('')

function addTab(sessionId: string, fundCode: string, fundName: string, direction?: 'buy' | 'sell' | 'hold') {
  const existing = openTabs.value.find(t => t.id === sessionId)
  if (existing) {
    if (direction) existing.direction = direction
    activeTabId.value = sessionId
    return
  }
  openTabs.value.push({ id: sessionId, fundCode, fundName, direction })
  activeTabId.value = sessionId
}

function switchTab(tabId: string) {
  activeTabId.value = tabId
  selectChat(tabId)
}

function closeTab(tabId: string) {
  const idx = openTabs.value.findIndex(t => t.id === tabId)
  if (idx === -1) return
  openTabs.value.splice(idx, 1)
  if (activeTabId.value === tabId) {
    if (openTabs.value.length > 0) {
      const newActive = openTabs.value[Math.min(idx, openTabs.value.length - 1)]
      if (newActive) {
        activeTabId.value = newActive.id
        selectChat(newActive.id)
      }
    } else {
      activeTabId.value = ''
    }
  }
}

watch(() => sessionStore.currentSession, (session) => {
  if (session) {
    const direction = analysisStore.currentReport?.decision?.shortTerm?.direction as 'buy' | 'sell' | 'hold' | undefined
    addTab(session.id, session.fundCode, session.fundName, direction)
  }
})

watch(() => analysisStore.currentReport, (report) => {
  if (report && sessionStore.currentSession) {
    const tab = openTabs.value.find(t => t.id === sessionStore.currentSession!.id)
    if (tab) {
      tab.direction = report.decision?.shortTerm?.direction as 'buy' | 'sell' | 'hold' | undefined
    }
  }
})

/* 同步 openTabs 与 sessionStore.sessions：会话被删除/清空时自动移除对应标签 */
watch(() => sessionStore.sessions, (sessions) => {
  const sessionIds = new Set(sessions.map(s => s.id))
  const wasActiveRemoved = openTabs.value.some(tab => !sessionIds.has(tab.id) && tab.id === activeTabId.value)
  /* 过滤掉已不存在的会话对应的标签 */
  openTabs.value = openTabs.value.filter(tab => sessionIds.has(tab.id))
  /* 如果当前激活的标签被移除，切换到剩余的第一个标签 */
  if (wasActiveRemoved) {
    const next = openTabs.value[0]
    if (next) {
      activeTabId.value = next.id
      selectChat(next.id)
    } else {
      activeTabId.value = ''
    }
  }
}, { deep: true })

/* ========== 组合式函数初始化 ========== */

/* 右键菜单管理 */
const {
  contextMenuVisible,
  contextMenuX,
  contextMenuY,
  handleRightClick,
  confirmDeleteSession,
  setupGlobalClickHandler,
  cleanupGlobalClickHandler,
} = useWorkspaceContextMenu()

/* SSE 流式事件处理（先创建，不注册处理器） */
const sse = useWorkspaceSSE({
  currentView,
  hasAutoSelectedAgent,
})

/* 分析流程管理（依赖 SSE 连接方法） */
const analysis = useWorkspaceAnalysis({
  headerFundInput,
  hasAutoSelectedAgent,
  currentView,
  connectToAnalysisStream: sse.connectToAnalysisStream,
  disconnectSSE: sse.disconnectSSE,
  markStreamEnded: sse.markStreamEnded,
})

/* 注册 SSE 事件处理器（需要 analysis.loadAnalysisReport 回调） */
sse.setupSSEHandlers(analysis.loadAnalysisReport)

/* ========== 计算属性 ========== */
const currentReport = analysis.currentReport
const isAnalyzing = analysis.isAnalyzing
const canReanalyze = analysis.canReanalyze
const agentList = computed(() => agentStore.agentList)

/* 当前基金信息（从当前会话获取） */
const currentFundCode = computed(() => sessionStore.currentSession?.fundCode || headerFundInput.value)
const currentFundName = computed(() => sessionStore.currentSession?.fundName || '')

/* 分析模式标签 */
const analysisModeLabel = computed(() => {
  const modeMap: Record<string, string> = {
    parallel: '并行分析',
    sequential: '串行分析',
  }
  return modeMap[analysisMode.value as string] || '并行分析'
})

/* 风险偏好标签 */
const riskPreferenceLabel = computed(() => {
  const prefMap: Record<string, string> = {
    conservative: '保守型',
    neutral: '稳健型',
    aggressive: '进取型',
  }
  return prefMap['neutral'] || '稳健型'
})

/* 已用时间计算 */
const elapsedTime = computed(() => {
  const agents = agentStore.agentList
  const runningAgent = agents.find(a => a.status === 'running')
  if (!runningAgent?.startTime) return ''
  const start = Number(runningAgent.startTime)
  const end = runningAgent.endTime ? Number(runningAgent.endTime) : Date.now()
  if (isNaN(start)) return ''
  const diff = Math.max(0, end - start)
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  return `${minutes}m ${remainSeconds}s`
})

/* ========== 方法 ========== */
const {
  startNewAnalysis,
  startReanalysis,
  togglePauseAnalysis,
  selectChat,
  showAgentDetail,
  showReportView,
  retryLoad,
} = analysis

/* ========== 生命周期 ========== */

onMounted(async () => {
  /* 初始化全局点击处理器（关闭右键菜单） */
  setupGlobalClickHandler()

  /* 执行页面初始化（会话加载、SSE连接等） */
  await analysis.initPage()
})

onUnmounted(() => {
  /* 断开 SSE 连接 */
  sse.disconnectSSE()

  /* 清理全局点击处理器 */
  cleanupGlobalClickHandler()
})
</script>

<style scoped>
.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: var(--space-10);
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-base);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-icon {
  width: 60px;
  height: 60px;
  background: var(--color-danger-50);
  border: 2px solid var(--color-danger-500);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-4xl);
  color: var(--color-danger-500);
  margin-bottom: var(--space-4);
}

.btn-retry {
  margin-top: var(--space-4);
  padding: var(--space-2) var(--space-5);
  background: var(--color-primary-500);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-retry:hover {
  background: var(--color-primary-600);
}
</style>
