<template>
  <div class="workspace-page">
    <!-- 顶部导航栏 -->
    <WorkspaceHeader
      :fund-input="headerFundInput"
      :is-analyzing="isAnalyzing"
      @update:fund-input="headerFundInput = $event"
      @start-analysis="startNewAnalysis"
      @open-settings="showSettings = true"
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

        <!-- 分析中状态 - 仅在报告视图时显示 -->
        <div v-else-if="isAnalyzing && currentView === 'report'" class="analyzing-container">
          <div class="analyzing-header">
            <h2>正在分析: {{ headerFundInput }}</h2>
            <div v-if="analysisStore.isPaused" class="pause-notice">分析已暂停</div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${agentStore.progress}%` }"></div>
            </div>
            <p>分析进度: {{ agentStore.progress }}%</p>
          </div>
          <div class="thinking-process">
            <h3>实时思考过程</h3>
            <div class="thinking-steps">
              <div
                v-for="(step, index) in recentThinkingSteps"
                :key="index"
                class="thinking-step"
              >
                <span class="step-time">{{ step.time }}</span>
                <span class="step-text">{{ step.text }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误状态 - 仅在报告视图时显示 -->
        <div v-else-if="analysisStore.error && currentView === 'report'" class="error-container">
          <div class="error-icon">!</div>
          <h3>加载失败</h3>
          <p>{{ analysisStore.error }}</p>
          <button class="btn-retry" @click="retryLoad">{{ sessionStore.currentSession?.status === 'failed' ? '重新分析' : '重试' }}</button>
        </div>

        <!-- 空状态 - 仅在报告视图时显示 -->
        <div v-else-if="!analysisStore.hasReport && currentView === 'report'" class="empty-container">
          <h3>开始分析基金</h3>
          <p>在顶部搜索框输入基金代码或名称，点击分析按钮开始</p>
        </div>

        <!-- 报告视图 -->
        <WorkspaceReportView
          v-else-if="currentView === 'report'"
          :report="currentReport"
        />

        <!-- 智能体思考过程视图 -->
        <WorkspaceAgentView
          v-if="currentView === 'agent' && currentAgentData"
          :agent-data="currentAgentData"
          :show-thinking-indicator="showThinkingIndicator"
          :is-paused="analysisStore.isPaused"
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

  <!-- 设置弹窗 -->
  <WorkspaceSettingsDialog
    v-model:show-settings="showSettings"
    :analysis-mode="analysisMode"
    @mode-change="handleModeChange"
  />
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
import { useAnalysisSettings, type AnalysisMode } from '~/composables/useAnalysisSettings'
import { useAgentStore } from '~/stores/agent'
import { useAnalysisStore } from '~/stores/analysis'
import { useSessionStore } from '~/stores/session'

/* ========== Store 初始化 ========== */
const agentStore = useAgentStore()
const analysisStore = useAnalysisStore()
const sessionStore = useSessionStore()
const { analysisMode, showSettings, saveMode } = useAnalysisSettings()

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
const currentAgentData = computed(() => agentStore.currentAgent)
const agentList = computed(() => agentStore.agentList)
const showThinkingIndicator = computed(() => isAnalyzing.value && currentAgentData.value?.status === 'running')
const recentThinkingSteps = computed(() => agentStore.thinkingProcess.slice(-10))

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

/* 处理分析模式切换 */
function handleModeChange(mode: string) {
  saveMode(mode as AnalysisMode)
}

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
.analyzing-container,
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

.analyzing-header {
  margin-bottom: var(--space-8);
}

.progress-bar {
  width: 300px;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin: var(--space-4) 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-success-500));
  transition: width 0.3s ease;
}

.thinking-process {
  width: 100%;
  max-width: 600px;
  text-align: left;
}

.thinking-steps {
  max-height: 300px;
  overflow-y: auto;
  padding: var(--space-4);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.thinking-step {
  padding: var(--space-2) 0;
  border-bottom: 1px dashed var(--border-base);
}

.thinking-step:last-child {
  border-bottom: none;
}

.step-time {
  color: var(--text-muted);
  margin-right: var(--space-3);
  font-size: var(--text-sm);
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

.pause-notice {
  margin: var(--space-2) 0;
  padding: var(--space-2) var(--space-4);
  background: var(--color-warning-50);
  border: 1px solid var(--color-warning-500);
  border-radius: var(--radius-sm);
  color: var(--color-warning-700);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
}
</style>
