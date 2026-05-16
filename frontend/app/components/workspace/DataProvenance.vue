<template>
  <div class="data-provenance">
    <span class="data-provenance__label">数据来源:</span>
    <template v-if="sources.length">
      <div
        v-for="(source, index) in sources"
        :key="index"
        class="data-provenance__item"
      >
        <span
          class="data-provenance__dot"
          :style="{ background: qualityColorMap[source.quality] }"
        ></span>
        <span class="data-provenance__name">{{ source.name }}</span>
        <span class="data-provenance__time">{{ source.updateTime }}</span>
      </div>
    </template>
    <span v-else class="data-provenance__default">公开市场数据</span>
  </div>
</template>

<script setup lang="ts">
interface Source {
  name: string
  updateTime: string
  quality: 'high' | 'medium' | 'low'
}

defineProps<{
  sources: Source[]
}>()

const qualityColorMap: Record<string, string> = {
  high: 'var(--color-success-500)',
  medium: 'var(--color-warning-500)',
  low: 'var(--color-danger-500)',
}
</script>

<style scoped>
.data-provenance {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.data-provenance__label {
  color: var(--text-muted);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.data-provenance__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.data-provenance__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.data-provenance__name {
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.data-provenance__time {
  color: var(--text-muted);
  font-family: var(--font-data);
}

.data-provenance__default {
  color: var(--text-muted);
}
</style>
