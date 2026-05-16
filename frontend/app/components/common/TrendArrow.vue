<template>
  <span class="trend-arrow" :class="[`trend-arrow--${direction}`, `trend-arrow--${size}`]">
    <span class="trend-arrow__icon">{{ arrowMap[direction] }}</span>
    <span v-if="showValue && value" class="trend-arrow__value">{{ value }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  direction: 'up' | 'down' | 'flat'
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
  value?: string
}

withDefaults(defineProps<Props>(), {
  size: 'md',
  showValue: false,
  value: ''
})

const arrowMap: Record<string, string> = {
  up: '↑',
  down: '↓',
  flat: '→'
}
</script>

<style scoped>
.trend-arrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-data);
  font-weight: var(--font-semibold);
  line-height: var(--leading-normal);
}

.trend-arrow--up {
  color: var(--color-rise);
}

.trend-arrow--down {
  color: var(--color-fall);
}

.trend-arrow--flat {
  color: var(--color-flat);
}

.trend-arrow--sm {
  font-size: var(--text-xs);
}

.trend-arrow--md {
  font-size: var(--text-sm);
}

.trend-arrow--lg {
  font-size: var(--text-lg);
}

.trend-arrow__icon {
  font-family: var(--font-data);
}

.trend-arrow--sm .trend-arrow__icon {
  font-size: 10px;
}

.trend-arrow--md .trend-arrow__icon {
  font-size: 12px;
}

.trend-arrow--lg .trend-arrow__icon {
  font-size: 16px;
}

.trend-arrow__value {
  font-family: var(--font-data);
}
</style>
