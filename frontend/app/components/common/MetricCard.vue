<template>
  <div class="metric-card" :class="[`metric-card--${variant}`]">
    <div class="metric-card__label">{{ label }}</div>
    <div class="metric-card__body">
      <span class="metric-card__value">{{ value }}</span>
      <span v-if="unit" class="metric-card__unit">{{ unit }}</span>
    </div>
    <div v-if="trend && trendValue" class="metric-card__trend" :class="`metric-card__trend--${trend}`">
      <span class="metric-card__arrow">{{ arrowMap[trend] }}</span>
      <span class="metric-card__trend-value">{{ trendValue }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  label: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | 'flat'
  trendValue?: string
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
}

withDefaults(defineProps<Props>(), {
  unit: '',
  trend: undefined,
  trendValue: '',
  variant: 'default'
})

const arrowMap: Record<string, string> = {
  up: '↑',
  down: '↓',
  flat: '→'
}
</script>

<style scoped>
.metric-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-base);
  transition: box-shadow var(--transition-base);
}

.metric-card:hover {
  box-shadow: var(--shadow-md);
}

.metric-card--primary {
  border-left: 3px solid var(--color-primary-500);
}

.metric-card--success {
  border-left: 3px solid var(--color-success-500);
}

.metric-card--warning {
  border-left: 3px solid var(--color-warning-500);
}

.metric-card--danger {
  border-left: 3px solid var(--color-danger-500);
}

.metric-card__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}

.metric-card__body {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}

.metric-card__value {
  font-family: var(--font-data);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: var(--leading-tight);
}

.metric-card__unit {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-muted);
}

.metric-card__trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.metric-card__trend--up {
  color: var(--color-rise);
}

.metric-card__trend--down {
  color: var(--color-fall);
}

.metric-card__trend--flat {
  color: var(--color-flat);
}

.metric-card__arrow {
  font-family: var(--font-data);
}

.metric-card__trend-value {
  font-family: var(--font-data);
}
</style>
