<template>
  <div class="quick-overview">
    <div class="quick-overview__header">
      <div class="quick-overview__fund">
        <span class="quick-overview__code">{{ fundCode }}</span>
        <span class="quick-overview__name">{{ fundName }}</span>
      </div>
      <div v-if="initialData.overallScore != null" class="quick-overview__gauge">
        <svg class="quick-overview__gauge-svg" viewBox="0 0 48 48">
          <circle
            class="quick-overview__gauge-track"
            cx="24" cy="24" r="20"
            fill="none"
            stroke-width="4"
          />
          <circle
            class="quick-overview__gauge-fill"
            cx="24" cy="24" r="20"
            fill="none"
            stroke-width="4"
            :stroke-dasharray="gaugeDash"
            :stroke-dashoffset="gaugeOffset"
            stroke-linecap="round"
          />
        </svg>
        <span class="quick-overview__gauge-value">{{ initialData.overallScore.toFixed(1) }}</span>
      </div>
    </div>

    <div class="quick-overview__body">
      <div v-if="initialData.direction" class="quick-overview__signal">
        <span class="quick-overview__signal-label">初步方向</span>
        <span class="quick-overview__signal-value" :class="`quick-overview__signal-value--${initialData.direction}`">
          {{ directionMap[initialData.direction] }}
        </span>
      </div>
      <div v-if="initialData.confidence != null" class="quick-overview__confidence">
        <span class="quick-overview__confidence-label">置信度</span>
        <div class="quick-overview__confidence-bar">
          <div
            class="quick-overview__confidence-fill"
            :style="{ width: `${initialData.confidence * 100}%` }"
          ></div>
        </div>
        <span class="quick-overview__confidence-text">{{ Math.round(initialData.confidence * 100) }}%</span>
      </div>
      <div v-if="initialData.topRisk" class="quick-overview__risk">
        <svg class="quick-overview__risk-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M8 1.5L14.5 13H1.5L8 1.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M8 6V9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="11" r="0.75" fill="currentColor"/>
        </svg>
        <span class="quick-overview__risk-text">{{ initialData.topRisk }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface InitialData {
  direction?: 'buy' | 'sell' | 'hold'
  confidence?: number
  topRisk?: string
  overallScore?: number
}

const props = withDefaults(defineProps<{
  fundCode: string
  fundName: string
  initialData: InitialData
}>(), {
  initialData: () => ({}),
})

const directionMap: Record<string, string> = {
  buy: '买入',
  sell: '卖出',
  hold: '持有',
}

const circumference = 2 * Math.PI * 20

const gaugeDash = computed(() => circumference)

const gaugeOffset = computed(() => {
  if (props.initialData.overallScore == null) return circumference
  const ratio = Math.min(Math.max(props.initialData.overallScore / 5, 0), 1)
  return circumference * (1 - ratio)
})
</script>

<style scoped>
.quick-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  animation: quick-overview-enter 0.4s ease-out both;
}

@keyframes quick-overview-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.quick-overview__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quick-overview__fund {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.quick-overview__code {
  font-family: var(--font-data);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.quick-overview__name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.quick-overview__gauge {
  position: relative;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
}

.quick-overview__gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.quick-overview__gauge-track {
  stroke: var(--bg-tertiary);
}

.quick-overview__gauge-fill {
  stroke: var(--color-primary-500);
  transition: stroke-dashoffset var(--transition-slow);
}

.quick-overview__gauge-value {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-data);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.quick-overview__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.quick-overview__signal {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.quick-overview__signal-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-weight: var(--font-medium);
}

.quick-overview__signal-value {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
}

.quick-overview__signal-value--buy {
  color: var(--color-buy);
  background: var(--color-buy-bg);
}

.quick-overview__signal-value--sell {
  color: var(--color-sell);
  background: var(--color-sell-bg);
}

.quick-overview__signal-value--hold {
  color: var(--color-hold);
  background: var(--color-hold-bg);
}

.quick-overview__confidence {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.quick-overview__confidence-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.quick-overview__confidence-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.quick-overview__confidence-fill {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: var(--radius-full);
  transition: width var(--transition-base);
}

.quick-overview__confidence-text {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  white-space: nowrap;
}

.quick-overview__risk {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--color-danger-50);
  border-radius: var(--radius-sm);
}

.quick-overview__risk-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--color-danger-500);
  margin-top: 1px;
}

.quick-overview__risk-text {
  font-size: var(--text-xs);
  color: var(--color-danger-600);
  line-height: var(--leading-normal);
}
</style>
