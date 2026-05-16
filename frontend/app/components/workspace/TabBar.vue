<template>
  <div class="tab-bar">
    <div class="tab-bar__scroll">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-bar__item"
        :class="{ 'tab-bar__item--active': tab.id === activeTabId }"
        @click="$emit('select', tab.id)"
      >
        <span
          v-if="tab.direction"
          class="tab-bar__dot"
          :class="`tab-bar__dot--${tab.direction}`"
        ></span>
        <span class="tab-bar__code">{{ tab.fundCode }}</span>
        <span class="tab-bar__name">{{ tab.fundName }}</span>
        <button
          v-if="tabs.length > 1"
          class="tab-bar__close"
          @click.stop="$emit('close', tab.id)"
        >
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M4 4l8 8M12 4l-8 8"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface TabItem {
  id: string
  fundCode: string
  fundName: string
  direction?: 'buy' | 'sell' | 'hold'
}

defineProps<{
  tabs: TabItem[]
  activeTabId: string
}>()

defineEmits<{
  select: [tabId: string]
  close: [tabId: string]
}>()
</script>

<style scoped>
.tab-bar {
  display: flex;
  align-items: flex-end;
  height: 36px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-base);
}

.tab-bar__scroll {
  display: flex;
  align-items: flex-end;
  overflow-x: auto;
  overflow-y: hidden;
  flex: 1;
  scrollbar-width: none;
}

.tab-bar__scroll::-webkit-scrollbar {
  display: none;
}

.tab-bar__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  height: 32px;
  padding: 0 var(--space-3);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background var(--transition-fast);
  position: relative;
  border-bottom: 2px solid transparent;
}

.tab-bar__item:hover {
  background: var(--bg-hover);
}

.tab-bar__item--active {
  background: var(--bg-elevated);
  border-bottom-color: var(--color-primary-500);
}

.tab-bar__item--active:hover {
  background: var(--bg-elevated);
}

.tab-bar__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.tab-bar__dot--buy {
  background: var(--color-buy);
}

.tab-bar__dot--sell {
  background: var(--color-sell);
}

.tab-bar__dot--hold {
  background: var(--color-hold);
}

.tab-bar__code {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
  line-height: var(--leading-tight);
}

.tab-bar__name {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: var(--leading-tight);
}

.tab-bar__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: color var(--transition-fast), opacity var(--transition-fast);
  flex-shrink: 0;
  margin-left: var(--space-1);
}

.tab-bar__item:hover .tab-bar__close {
  opacity: 1;
}

.tab-bar__close:hover {
  color: var(--color-danger-500);
}
</style>
