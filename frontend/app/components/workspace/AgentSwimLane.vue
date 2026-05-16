<template>
  <div class="agent-swimlane">
    <div
      v-for="agent in agents"
      :key="agent.type"
      class="swimlane"
      :class="[`swimlane--${agent.status}`]"
    >
      <div class="swimlane__info">
        <span class="swimlane__name">{{ agent.name }}</span>
        <span class="swimlane__status" :class="[`swimlane__status--${agent.status}`]">
          {{ statusText[agent.status] }}
        </span>
      </div>
      <div class="swimlane__track">
        <div
          class="swimlane__bar"
          :class="[`swimlane__bar--${agent.status}`]"
          :style="barStyle(agent)"
        >
          <span v-if="agent.status === 'completed'" class="swimlane__check">&#10003;</span>
          <span v-if="agent.status === 'running' && agent.progress != null" class="swimlane__progress-text">
            {{ agent.progress }}%
          </span>
        </div>
      </div>
      <div v-if="agent.startTime" class="swimlane__time">
        {{ formatDuration(agent) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Agent {
  type: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'error'
  startTime?: number
  endTime?: number
  progress?: number
}

defineProps<{
  agents: Agent[]
}>()

const statusText: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  error: '出错',
}

function barStyle(agent: Agent) {
  if (agent.status === 'running' && agent.progress != null) {
    return { width: `${Math.min(Math.max(agent.progress, 0), 100)}%` }
  }
  if (agent.status === 'completed') {
    return { width: '100%' }
  }
  if (agent.status === 'error') {
    return { width: '100%' }
  }
  return { width: '0%' }
}

function formatDuration(agent: Agent) {
  if (!agent.startTime) return ''
  const end = agent.endTime || Date.now()
  const diff = Math.max(0, end - agent.startTime)
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  return `${minutes}m${remainSeconds}s`
}
</script>

<style scoped>
.agent-swimlane {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.swimlane {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  transition: border-color var(--transition-fast);
}

.swimlane--running {
  border-color: var(--color-primary-200);
}

.swimlane--completed {
  border-color: var(--color-success-100);
}

.swimlane--error {
  border-color: var(--color-danger-100);
}

.swimlane__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 120px;
}

.swimlane__name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.swimlane__status {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.swimlane__status--pending {
  color: var(--color-gray-400);
}

.swimlane__status--running {
  color: var(--color-primary-500);
}

.swimlane__status--completed {
  color: var(--color-success-500);
}

.swimlane__status--error {
  color: var(--color-danger-500);
}

.swimlane__track {
  flex: 1;
  height: 24px;
  background: var(--color-gray-100);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

.swimlane__bar {
  height: 100%;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width var(--transition-slow);
  position: relative;
}

.swimlane__bar--pending {
  background: var(--color-gray-200);
}

.swimlane__bar--running {
  background: linear-gradient(90deg, var(--color-primary-400), var(--color-primary-500));
  animation: swimlane-pulse 2s ease-in-out infinite;
}

.swimlane__bar--completed {
  background: var(--color-success-500);
}

.swimlane__bar--error {
  background: var(--color-danger-500);
}

.swimlane__check {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--text-inverse);
}

.swimlane__progress-text {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-inverse);
}

.swimlane__time {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-width: 48px;
  text-align: right;
}

@keyframes swimlane-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
