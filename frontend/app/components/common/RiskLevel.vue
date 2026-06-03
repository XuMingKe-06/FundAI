<template>
  <span class="risk-level" :class="[`risk-level--${level}`]">
    <span class="risk-level__dot"></span>
    <span v-if="showLabel" class="risk-level__label">{{ labelMap[level] }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  level: 'low' | 'medium' | 'high'
  showLabel?: boolean
}

withDefaults(defineProps<Props>(), {
  showLabel: true
})

const labelMap: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险'
}
</script>

<style scoped>
.risk-level {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: var(--leading-normal);
}

.risk-level--low {
  background: var(--color-risk-low-bg);
  color: var(--color-risk-low);
}

.risk-level--medium {
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
}

.risk-level--high {
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
}

.risk-level__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.risk-level--low .risk-level__dot {
  background: var(--color-risk-low);
}

.risk-level--medium .risk-level__dot {
  background: var(--color-risk-medium);
}

.risk-level--high .risk-level__dot {
  background: var(--color-risk-high);
}

.risk-level__label {
  white-space: nowrap;
}
</style>
