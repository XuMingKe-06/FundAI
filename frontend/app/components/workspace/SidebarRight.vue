<template>
  <aside class="sidebar-right">
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
  </aside>
</template>

<script setup lang="ts">
/* 工作台右侧智能体进度栏组件 */

import { getAgentStatusText, formatAgentScore } from '~/utils/format'
import { renderMarkdown } from '~/utils/markdown'
import type { AgentInfo, AgentType } from '~/stores/agent'

defineProps<{
  /* 智能体列表 */
  agentList: AgentInfo[]
  /* 是否正在分析 */
  isAnalyzing: boolean
  /* 是否可以重新分析 */
  canReanalyze: boolean
  /* 分析是否暂停 */
  isPaused: boolean
}>()

defineEmits<{
  /* 重新分析 */
  'reanalyze': []
  /* 暂停/继续分析切换 */
  'togglePause': []
  /* 显示报告视图 */
  'showReport': []
  /* 显示智能体详情 */
  'showAgentDetail': [agentType: AgentType]
}>()
</script>

<style scoped>
@import '~/assets/css/markdown.css';

.sidebar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-reanalyze {
  padding: 4px 10px;
  background: #E6A23C;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-reanalyze:hover {
  background: #ebb563;
}

.btn-pause {
  padding: 4px 10px;
  background: #E6A23C;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-pause:hover {
  background: #ebb563;
}

.btn-resume {
  padding: 4px 10px;
  background: #67C23A;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-resume:hover {
  background: #85ce61;
}
</style>
