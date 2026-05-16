<template>
  <div class="holdings-table">
    <CommonDataTable
      :columns="columns"
      :data="holdings"
      :stripe="true"
      empty-text="暂无持仓数据"
    >
      <template #cell-holdingRatio="{ value }">
        <div class="holding-ratio">
          <div class="holding-ratio__bar-track">
            <div
              class="holding-ratio__bar-fill"
              :style="{ width: `${Math.min(value, 100)}%` }"
            ></div>
          </div>
          <span class="holding-ratio__text">{{ value.toFixed(2) }}%</span>
        </div>
      </template>
      <template #cell-change="{ value }">
        <span v-if="value != null" class="change-value" :class="changeClass(value)">
          {{ value > 0 ? '+' : '' }}{{ value.toFixed(2) }}%
        </span>
        <span v-else class="change-value change-value--flat">--</span>
      </template>
    </CommonDataTable>
  </div>
</template>

<script setup lang="ts">
interface Holding {
  stockCode: string
  stockName: string
  holdingRatio: number
  change?: number
  industry?: string
}

defineProps<{
  holdings: Holding[]
}>()

const columns = [
  { key: 'stockCode', label: '股票代码', width: '100px', align: 'center' as const },
  { key: 'stockName', label: '股票名称', width: '120px' },
  { key: 'holdingRatio', label: '持仓比例', width: '180px' },
  { key: 'change', label: '变动', width: '100px', align: 'right' as const },
  { key: 'industry', label: '行业' },
]

function changeClass(value: number) {
  if (value > 0) return 'change-value--rise'
  if (value < 0) return 'change-value--fall'
  return 'change-value--flat'
}
</script>

<style scoped>
.holdings-table {
  width: 100%;
}

.holding-ratio {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.holding-ratio__bar-track {
  flex: 1;
  height: 6px;
  background: var(--color-gray-100);
  border-radius: var(--radius-full);
  overflow: hidden;
  min-width: 60px;
}

.holding-ratio__bar-fill {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: var(--radius-full);
  transition: width var(--transition-base);
}

.holding-ratio__text {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
  min-width: 52px;
  text-align: right;
}

.change-value {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.change-value--rise {
  color: var(--color-rise);
}

.change-value--fall {
  color: var(--color-fall);
}

.change-value--flat {
  color: var(--color-flat);
}
</style>
