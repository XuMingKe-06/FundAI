<template>
  <div class="data-table" :class="{ 'data-table--bordered': border }">
    <div class="data-table__wrapper" :style="maxHeight ? { maxHeight } : undefined">
      <table class="data-table__table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :style="getColStyle(col)"
              :class="{ 'data-table__th--sortable': col.sortable }"
              @click="col.sortable && handleSort(col.key)"
            >
              <span class="data-table__th-content">
                <span class="data-table__th-label">{{ col.label }}</span>
                <span v-if="col.sortable" class="data-table__sort">
                  <span
                    class="data-table__sort-icon"
                    :class="{
                      'data-table__sort-icon--active': sortKey === col.key && sortOrder === 'asc'
                    }"
                  >▲</span>
                  <span
                    class="data-table__sort-icon"
                    :class="{
                      'data-table__sort-icon--active': sortKey === col.key && sortOrder === 'desc'
                    }"
                  >▼</span>
                </span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rowIndex) in sortedData"
            :key="rowIndex"
            class="data-table__row"
            :class="{ 'data-table__row--stripe': stripe && rowIndex % 2 === 1 }"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :style="getColStyle(col)"
              :class="getCellClass(col, row[col.key])"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                <template v-if="col.type === 'rise'">
                  <span class="data-table__cell--rise">{{ row[col.key] }}</span>
                </template>
                <template v-else-if="col.type === 'fall'">
                  <span class="data-table__cell--fall">{{ row[col.key] }}</span>
                </template>
                <template v-else-if="col.type === 'tag'">
                  <span class="data-table__cell-tag">{{ row[col.key] }}</span>
                </template>
                <template v-else>
                  {{ row[col.key] }}
                </template>
              </slot>
            </td>
          </tr>
          <tr v-if="sortedData.length === 0">
            <td :colspan="columns.length" class="data-table__empty">
              {{ emptyText }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Column {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  type?: 'default' | 'rise' | 'fall' | 'tag'
}

interface Props {
  columns: Column[]
  data: Array<Record<string, any>>
  stripe?: boolean
  border?: boolean
  maxHeight?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  stripe: true,
  border: false,
  maxHeight: '',
  emptyText: '暂无数据'
})

const sortKey = ref('')
const sortOrder = ref<'asc' | 'desc'>('asc')

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  const key = sortKey.value
  const order = sortOrder.value
  return [...props.data].sort((a, b) => {
    const valA = a[key]
    const valB = b[key]
    if (valA == null && valB == null) return 0
    if (valA == null) return 1
    if (valB == null) return -1
    let result = 0
    if (typeof valA === 'number' && typeof valB === 'number') {
      result = valA - valB
    } else {
      result = String(valA).localeCompare(String(valB), 'zh-CN')
    }
    return order === 'asc' ? result : -result
  })
})

function handleSort(key: string) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

function getColStyle(col: Column) {
  const style: Record<string, string> = {}
  if (col.width) style.width = col.width
  if (col.align) style.textAlign = col.align
  return style
}

function getCellClass(col: Column, _value: any) {
  const classes: string[] = []
  if (col.align) classes.push(`data-table__cell--${col.align}`)
  return classes
}
</script>

<style scoped>
.data-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
}

.data-table--bordered {
  border: 1px solid var(--border-base);
}

.data-table--bordered th,
.data-table--bordered td {
  border: 1px solid var(--border-base);
}

.data-table__wrapper {
  overflow-x: auto;
  overflow-y: auto;
}

.data-table__table {
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
}

thead {
  background: var(--bg-tertiary);
}

th {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border-base);
  user-select: none;
}

.data-table__th--sortable {
  cursor: pointer;
  transition: color var(--transition-fast);
}

.data-table__th--sortable:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.data-table__th-content {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.data-table__sort {
  display: inline-flex;
  flex-direction: column;
  line-height: 1;
  gap: 0;
}

.data-table__sort-icon {
  font-size: 8px;
  line-height: 1;
  color: var(--text-muted);
  transition: color var(--transition-fast);
}

.data-table__sort-icon--active {
  color: var(--color-primary-500);
}

td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition-fast);
}

.data-table__cell--left {
  text-align: left;
}

.data-table__cell--center {
  text-align: center;
}

.data-table__cell--right {
  text-align: right;
}

.data-table__row:hover td {
  background: var(--bg-hover);
}

.data-table__row--stripe td {
  background: var(--bg-secondary);
}

.data-table__row--stripe:hover td {
  background: var(--bg-hover);
}

.data-table__cell--rise {
  color: var(--color-rise);
  font-family: var(--font-data);
  font-weight: var(--font-medium);
}

.data-table__cell--fall {
  color: var(--color-fall);
  font-family: var(--font-data);
  font-weight: var(--font-medium);
}

.data-table__cell-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-gray-100);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.data-table__empty {
  padding: var(--space-10) var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  background: var(--bg-secondary);
}
</style>
