<template>
  <div class="nav-history-table">
    <CommonDataTable
      :columns="columns"
      :data="navData"
      :stripe="true"
      max-height="400px"
      empty-text="暂无净值数据"
    >
      <template #cell-nav="{ value }">
        <span class="nav-value">{{ value.toFixed(4) }}</span>
      </template>
      <template #cell-accNav="{ value }">
        <span class="nav-value">{{ value.toFixed(4) }}</span>
      </template>
      <template #cell-dailyReturn="{ value }">
        <span class="return-value" :class="returnClass(value)">
          {{ value > 0 ? '+' : '' }}{{ value.toFixed(2) }}%
        </span>
      </template>
    </CommonDataTable>
  </div>
</template>

<script setup lang="ts">
interface NavItem {
  date: string
  nav: number
  accNav: number
  dailyReturn: number
}

defineProps<{
  navData: NavItem[]
}>()

const columns = [
  { key: 'date', label: '日期', width: '120px', sortable: true },
  { key: 'nav', label: '单位净值', width: '120px', align: 'right' as const },
  { key: 'accNav', label: '累计净值', width: '120px', align: 'right' as const },
  { key: 'dailyReturn', label: '日涨跌幅', width: '120px', align: 'right' as const, sortable: true },
]

function returnClass(value: number) {
  if (value > 0) return 'return-value--rise'
  if (value < 0) return 'return-value--fall'
  return 'return-value--flat'
}
</script>

<style scoped>
.nav-history-table {
  width: 100%;
}

.nav-value {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.return-value {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.return-value--rise {
  color: var(--color-rise);
}

.return-value--fall {
  color: var(--color-fall);
}

.return-value--flat {
  color: var(--color-flat);
}
</style>
