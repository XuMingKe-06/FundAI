<template>
  <div class="tool-call-viz">
    <div
      v-for="(call, index) in toolCalls"
      :key="index"
      class="tool-call-viz__item"
    >
      <div class="tool-call-viz__timeline">
        <div class="tool-call-viz__dot" :class="`tool-call-viz__dot--${call.status}`">
          <svg v-if="call.status === 'success'" class="tool-call-viz__status-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
            <path d="M5 8L7 10L11 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <svg v-else-if="call.status === 'error'" class="tool-call-viz__status-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
            <path d="M6 6L10 10M10 6L6 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <svg v-else class="tool-call-viz__status-icon tool-call-viz__status-icon--spinning" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5" stroke-dasharray="22 22" stroke-linecap="round"/>
          </svg>
        </div>
        <div v-if="index < toolCalls.length - 1" class="tool-call-viz__line"></div>
      </div>
      <div class="tool-call-viz__content">
        <div class="tool-call-viz__header">
          <span class="tool-call-viz__name">{{ getToolChineseName(call.toolName) }}</span>
          <span v-if="call.duration != null" class="tool-call-viz__duration">{{ formatDuration(call.duration) }}</span>
        </div>
        <div v-if="call.dataDesc" class="tool-call-viz__desc">{{ call.dataDesc }}</div>
        <span
          v-if="call.quality"
          class="tool-call-viz__quality"
          :class="`tool-call-viz__quality--${call.quality}`"
        >
          {{ qualityLabelMap[call.quality] }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getToolChineseName } from '~/utils/toolNameMap'

interface ToolCall {
  toolName: string
  status: 'calling' | 'success' | 'error'
  dataDesc?: string
  quality?: 'complete' | 'partial' | 'stale'
  duration?: number
}

defineProps<{
  toolCalls: ToolCall[]
}>()

const qualityLabelMap: Record<string, string> = {
  complete: '完整',
  partial: '部分',
  stale: '过期',
}

function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`
  }
  return `${ms}ms`
}
</script>

<style scoped>
.tool-call-viz {
  display: flex;
  flex-direction: column;
}

.tool-call-viz__item {
  display: flex;
  gap: var(--space-3);
  min-height: 40px;
}

.tool-call-viz__timeline {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
}

.tool-call-viz__dot {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tool-call-viz__dot--calling {
  color: var(--color-primary-500);
}

.tool-call-viz__dot--success {
  color: var(--color-success-500);
}

.tool-call-viz__dot--error {
  color: var(--color-danger-500);
}

.tool-call-viz__status-icon {
  width: 16px;
  height: 16px;
}

.tool-call-viz__status-icon--spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.tool-call-viz__line {
  width: 1px;
  flex: 1;
  background: var(--border-base);
  margin: var(--space-1) 0;
}

.tool-call-viz__content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-bottom: var(--space-4);
  min-width: 0;
}

.tool-call-viz__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.tool-call-viz__name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.tool-call-viz__duration {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.tool-call-viz__desc {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}

.tool-call-viz__quality {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  width: fit-content;
}

.tool-call-viz__quality--complete {
  color: var(--color-success-600);
  background: var(--color-success-50);
}

.tool-call-viz__quality--partial {
  color: var(--color-warning-600);
  background: var(--color-warning-50);
}

.tool-call-viz__quality--stale {
  color: var(--color-danger-600);
  background: var(--color-danger-50);
}
</style>
