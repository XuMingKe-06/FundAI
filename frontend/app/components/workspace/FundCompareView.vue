<template>
  <div class="fund-compare">
    <div class="fund-compare__header">
      <div class="fund-compare__label-col"></div>
      <div
        v-for="fund in visibleFunds"
        :key="fund.fundCode"
        class="fund-compare__fund-col"
      >
        <span class="fund-compare__fund-code">{{ fund.fundCode }}</span>
        <span class="fund-compare__fund-name">{{ fund.fundName }}</span>
      </div>
    </div>
    <div class="fund-compare__body">
      <div
        v-for="metric in metrics"
        :key="metric.key"
        class="fund-compare__row"
      >
        <div class="fund-compare__label-col">
          <span class="fund-compare__metric-label">{{ metric.label }}</span>
        </div>
        <div
          v-for="(fund, idx) in visibleFunds"
          :key="fund.fundCode"
          class="fund-compare__fund-col"
        >
          <span
            class="fund-compare__metric-value"
            :class="{ 'fund-compare__metric-value--best': isBest(metric, idx) }"
          >
            {{ formatMetric(metric, fund) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Fund {
  fundCode: string
  fundName: string
  volatility?: number
  maxDrawdown?: number
  sharpeRatio?: number
  annualReturn?: number
  styleBox?: string
}

interface MetricDef {
  key: keyof Fund
  label: string
  format: (val: any) => string
  bestDirection: 'max' | 'min' | 'none'
}

const props = defineProps<{
  funds: Fund[]
}>()

const visibleFunds = computed(() => props.funds.slice(0, 5))

const metrics: MetricDef[] = [
  { key: 'annualReturn', label: '年化收益', format: (v) => v != null ? `${(v as number).toFixed(2)}%` : '--', bestDirection: 'max' },
  { key: 'volatility', label: '波动率', format: (v) => v != null ? `${(v as number).toFixed(2)}%` : '--', bestDirection: 'min' },
  { key: 'maxDrawdown', label: '最大回撤', format: (v) => v != null ? `${(v as number).toFixed(2)}%` : '--', bestDirection: 'min' },
  { key: 'sharpeRatio', label: '夏普比率', format: (v) => v != null ? (v as number).toFixed(2) : '--', bestDirection: 'max' },
  { key: 'styleBox', label: '风格箱', format: (v) => v ?? '--', bestDirection: 'none' },
]

function formatMetric(metric: MetricDef, fund: Fund) {
  return metric.format(fund[metric.key])
}

function isBest(metric: MetricDef, fundIndex: number): boolean {
  if (metric.bestDirection === 'none') return false
  const funds = visibleFunds.value
  const values = funds.map(f => f[metric.key] as number | undefined).filter(v => v != null) as number[]
  if (values.length === 0) return false
  const targetVal = funds[fundIndex]?.[metric.key] as number | undefined
  if (targetVal == null) return false
  if (metric.bestDirection === 'max') return targetVal === Math.max(...values)
  return targetVal === Math.min(...values)
}
</script>

<style scoped>
.fund-compare {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-base);
  background: var(--bg-elevated);
}

.fund-compare__header {
  display: grid;
  grid-template-columns: minmax(100px, 1fr) repeat(v-bind('visibleFunds.length'), minmax(0, 1fr));
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-base);
}

.fund-compare__label-col {
  padding: var(--space-3) var(--space-4);
}

.fund-compare__fund-col {
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  border-left: 1px solid var(--border-light);
}

.fund-compare__fund-code {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.fund-compare__fund-name {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.fund-compare__body {
  display: flex;
  flex-direction: column;
}

.fund-compare__row {
  display: grid;
  grid-template-columns: minmax(100px, 1fr) repeat(v-bind('visibleFunds.length'), minmax(0, 1fr));
  border-bottom: 1px solid var(--border-light);
}

.fund-compare__row:last-child {
  border-bottom: none;
}

.fund-compare__row .fund-compare__label-col {
  display: flex;
  align-items: center;
}

.fund-compare__row .fund-compare__fund-col {
  justify-content: center;
}

.fund-compare__metric-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.fund-compare__metric-value {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.fund-compare__metric-value--best {
  background: var(--color-success-500);
  color: var(--text-inverse);
  font-weight: var(--font-semibold);
}
</style>
