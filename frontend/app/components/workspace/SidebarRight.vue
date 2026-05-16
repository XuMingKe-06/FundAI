<template>
  <aside class="sidebar-right" :class="{ collapsed: collapsed }">
    <template v-if="!collapsed">
      <div class="sidebar-header">
        <h3>智能体进度</h3>
        <div class="sidebar-actions">
          <button v-if="canReanalyze" class="btn-reanalyze" @click="$emit('reanalyze')">重新分析</button>
          <button v-if="isAnalyzing && !isPaused" class="btn-pause" @click="$emit('togglePause')">暂停分析</button>
          <button v-if="isAnalyzing && isPaused" class="btn-resume" @click="$emit('togglePause')">继续分析</button>
          <button class="btn-report" @click="$emit('showReport')">报告</button>
        </div>
      </div>
      <div class="agent-list">
        <div
          v-for="agent in agentList"
          :key="agent.type"
          class="agent-item"
          :class="[agent.status, { decision: agent.type === 'decision' }]"
          @click="$emit('showAgentDetail', agent.type)"
        >
          <div class="agent-header">
            <span class="agent-name">{{ agent.name }}</span>
            <span class="agent-score">{{ formatAgentScore(agent) }}</span>
            <span class="agent-status">{{ getAgentStatusText(agent.status) }}</span>
          </div>
          <div class="agent-summary md-content md-summary" v-html="renderMarkdown(agent.summary || '等待分析...')"></div>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="collapsed-agent-list">
        <div
          v-for="agent in agentList"
          :key="agent.type"
          class="collapsed-agent-item"
          :class="agent.status"
          :title="`${agent.name} ${formatAgentScore(agent)}`"
          @click="$emit('showAgentDetail', agent.type)"
        >
          <span class="collapsed-agent-dot"></span>
        </div>
      </div>
    </template>
    <button class="btn-collapse" :title="collapsed ? '展开侧边栏' : '折叠侧边栏'" @click="$emit('toggleCollapse')">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline v-if="collapsed" points="15 18 9 12 15 6"/>
        <polyline v-else points="9 18 15 12 9 6"/>
      </svg>
    </button>
  </aside>
</template>

<script setup lang="ts">
import { getAgentStatusText, formatAgentScore } from '~/utils/format'
import { renderMarkdown } from '~/utils/markdown'
import type { AgentInfo, AgentType } from '~/stores/agent'

defineProps<{
  agentList: AgentInfo[]
  isAnalyzing: boolean
  canReanalyze: boolean
  isPaused: boolean
  collapsed: boolean
}>()

defineEmits<{
  'reanalyze': []
  'togglePause': []
  'showReport': []
  'showAgentDetail': [agentType: AgentType]
  'toggleCollapse': []
}>()
</script>

<style scoped>
@import '~/assets/css/markdown.css';

.sidebar-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
}

.btn-reanalyze,
.btn-pause {
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning-500);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.btn-reanalyze:hover,
.btn-pause:hover {
  opacity: 0.85;
}

.btn-resume {
  padding: var(--space-1) var(--space-2);
  background: var(--color-success-500);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.btn-resume:hover {
  opacity: 0.85;
}

.collapsed-agent-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.collapsed-agent-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.collapsed-agent-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-gray-400);
}

.collapsed-agent-item.running .collapsed-agent-dot {
  background: var(--color-primary-500);
  animation: pulse 1.5s infinite;
}

.collapsed-agent-item.completed .collapsed-agent-dot {
  background: var(--color-success-500);
}

.collapsed-agent-item.error .collapsed-agent-dot {
  background: var(--color-danger-500);
}

.collapsed-agent-item:hover {
  background: var(--bg-hover);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.btn-collapse {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 36px;
  border: none;
  border-top: 1px solid var(--border-base);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-collapse:hover {
  background: var(--bg-hover);
  color: var(--color-primary-500);
}
</style>
