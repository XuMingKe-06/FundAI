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
        @update:search="sidebarSearch = $event"
        @select-session="selectChat"
        @right-click="handleRightClick"
        @delete-session="confirmDeleteSession"
      />

      <!-- 中间主内容区 -->
      <main class="main-content">
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
        @reanalyze="startReanalysis"
        @toggle-pause="togglePauseAnalysis"
        @show-report="showReportView"
        @show-agent-detail="showAgentDetail"
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

  /* 执行页面初始化（认证检查、会话加载、SSE连接等） */
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
/* 加载/分析中/错误/空状态容器 */
.loading-container,
.analyzing-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 40px;
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e0e0e0;
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 分析中状态样式 */
.analyzing-header {
  margin-bottom: 30px;
}

.progress-bar {
  width: 300px;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin: 15px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #409EFF, #67C23A);
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
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.thinking-step {
  padding: 8px 0;
  border-bottom: 1px dashed #e0e0e0;
}

.thinking-step:last-child {
  border-bottom: none;
}

.step-time {
  color: #909399;
  margin-right: 10px;
  font-size: 12px;
}

/* 错误状态样式 */
.error-icon {
  width: 60px;
  height: 60px;
  background: #fef0f0;
  border: 2px solid #f56c6c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #f56c6c;
  margin-bottom: 15px;
}

.btn-retry {
  margin-top: 15px;
  padding: 8px 20px;
  background: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-retry:hover {
  background: #66b1ff;
}

/* 暂停提示 */
.pause-notice {
  margin: 8px 0;
  padding: 6px 16px;
  background: #fdf6ec;
  border: 1px solid #E6A23C;
  border-radius: 4px;
  color: #E6A23C;
  font-size: 14px;
  font-weight: 500;
}
</style>
