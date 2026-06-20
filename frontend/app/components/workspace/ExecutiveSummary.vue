<template>
  <div class="executive-summary">
    <div class="summary-header">
      <div class="fund-info">
        <span class="fund-code">{{ fundCode }}</span>
        <span class="fund-name">{{ fundName }}</span>
      </div>
      <span class="update-time">{{ formattedTime }}</span>
    </div>

    <div class="decision-row">
      <div class="signal-card signal-card--short">
        <div class="signal-card__border" :style="{ background: 'var(--color-short-term)' }"></div>
        <div class="signal-card__body">
          <div class="signal-card__label">短线建议（7-30天）</div>
          <div class="signal-card__direction" :class="`direction--${shortTermDirection}`">
            {{ directionMap[shortTermDirection] }}
          </div>
          <div class="signal-card__confidence">
            <span class="confidence-text">置信率：{{ Math.round(shortTermConfidence * 100) }}%</span>
          </div>
          <div class="signal-card__period">建议持有期：7-30天</div>
        </div>
      </div>

      <div class="signal-card signal-card--long">
        <div class="signal-card__border" :style="{ background: 'var(--color-long-term)' }"></div>
        <div class="signal-card__body">
          <div class="signal-card__label">长线建议（6个月以上）</div>
          <div class="signal-card__direction" :class="`direction--${longTermDirection}`">
            {{ directionMap[longTermDirection] }}
          </div>
          <div class="signal-card__confidence">
            <span class="confidence-text">置信率：{{ Math.round(longTermConfidence * 100) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <div class="viewpoints-row">
      <div class="viewpoint-card">
        <div class="viewpoint-card__label">综合评分</div>
        <div class="viewpoint-card__value viewpoint-card__value--primary">
          {{ scores.overall.toFixed(1) }}
        </div>
      </div>
      <div class="viewpoint-card">
        <div class="viewpoint-card__label">风险等级</div>
        <div class="viewpoint-card__value" :class="`viewpoint-card__value--risk-${riskLevel}`">
          <span class="risk-dot"></span>
          {{ riskLevelText }}
        </div>
      </div>
      <div class="viewpoint-card">
        <div class="viewpoint-card__label">成本评分</div>
        <div class="viewpoint-card__value">
          {{ scores.cost.toFixed(1) }}
        </div>
      </div>
    </div>

    <div class="risks-row" v-if="riskAlerts.length">
      <div class="risks-row__header">
        <svg class="risks-row__icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M8 1.5L14.5 13H1.5L8 1.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M8 6V9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="11" r="0.75" fill="currentColor"/>
        </svg>
        <span class="risks-row__title">关键风险</span>
      </div>
      <div class="risks-row__list">
        <div
          v-for="(alert, index) in topRiskAlerts"
          :key="index"
          class="risk-item"
        >
          <svg class="risk-item__icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 5V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="8" cy="10.75" r="0.75" fill="currentColor"/>
          </svg>
          <span class="risk-item__text">{{ alert }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Scores {
  fundamental: number
  technical: number
  risk: number
  cost: number
  sentiment: number
  overall: number
}

type Direction = 'buy' | 'sell' | 'hold'

const props = withDefaults(defineProps<{
  fundCode: string
  fundName: string
  shortTermDirection: Direction
  longTermDirection: Direction
  shortTermConfidence: number
  longTermConfidence: number
  scores: Scores
  riskAlerts: string[]
}>(), {
  shortTermDirection: 'hold',
  longTermDirection: 'hold',
  shortTermConfidence: 0,
  longTermConfidence: 0,
  riskAlerts: () => [],
})

const directionMap: Record<Direction, string> = {
  buy: '买入',
  sell: '卖出',
  hold: '持有',
}

const formattedTime = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const h = String(now.getHours()).padStart(2, '0')
  const min = String(now.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${min}`
})

const riskLevel = computed<'low' | 'medium' | 'high'>(() => {
  const r = props.scores.risk
  if (r >= 4) return 'low'
  if (r >= 2.5) return 'medium'
  return 'high'
})

const riskLevelText = computed(() => {
  const map: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return map[riskLevel.value]
})

const topRiskAlerts = computed(() => props.riskAlerts.slice(0, 3))
</script>

<style scoped>
.executive-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.fund-info {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.fund-code {
  font-family: var(--font-data);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.fund-name {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.update-time {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-family: var(--font-data);
}

.decision-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.signal-card {
  display: flex;
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow var(--transition-fast);
}

.signal-card:hover {
  box-shadow: var(--shadow-md);
}

.signal-card__border {
  width: 4px;
  flex-shrink: 0;
}

.signal-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
}

.signal-card__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-muted);
}

.signal-card__direction {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
}

.direction--buy {
  color: var(--color-buy);
  background: var(--color-buy-bg);
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-base);
}

.direction--sell {
  color: var(--color-sell);
  background: var(--color-sell-bg);
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-base);
}

.direction--hold {
  color: var(--color-hold);
  background: var(--color-hold-bg);
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-base);
}

.signal-card__confidence {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.confidence-text {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  white-space: nowrap;
}

.signal-card__period {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.viewpoints-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-3);
}

.viewpoint-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}

.viewpoint-card__label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-muted);
}

.viewpoint-card__value {
  font-family: var(--font-data);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: var(--leading-tight);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.viewpoint-card__value--primary {
  color: var(--color-primary-500);
}

.viewpoint-card__value--risk-low {
  color: var(--color-risk-low);
}

.viewpoint-card__value--risk-medium {
  color: var(--color-risk-medium);
}

.viewpoint-card__value--risk-high {
  color: var(--color-risk-high);
}

.risk-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.viewpoint-card__value--risk-low .risk-dot {
  background: var(--color-risk-low);
}

.viewpoint-card__value--risk-medium .risk-dot {
  background: var(--color-risk-medium);
}

.viewpoint-card__value--risk-high .risk-dot {
  background: var(--color-risk-high);
}

.risks-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-danger-50);
  border: 1px solid var(--color-danger-100);
  border-radius: var(--radius-md);
}

.risks-row__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-danger-500);
}

.risks-row__icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.risks-row__title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.risks-row__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.risk-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.risk-item__icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--color-danger-500);
}

.risk-item__text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}
</style>
