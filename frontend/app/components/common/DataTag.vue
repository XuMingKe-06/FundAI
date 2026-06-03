<template>
  <span class="data-tag" :class="[`data-tag--${type}`]">
    <span class="data-tag__label">{{ label }}</span>
    <span class="data-tag__value">{{ value }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  label: string
  value: string | number
  type?: 'default' | 'rise' | 'fall' | 'flat' | 'primary' | 'warning' | 'danger'
}

withDefaults(defineProps<Props>(), {
  type: 'default'
})
</script>

<style scoped>
.data-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.data-tag--default {
  background: var(--color-gray-100);
  color: var(--text-secondary);
}

.data-tag--default .data-tag__value {
  color: var(--text-primary);
}

.data-tag--rise {
  background: var(--color-rise-bg);
  color: var(--color-rise);
}

.data-tag--rise .data-tag__value {
  color: var(--color-rise);
  font-weight: var(--font-semibold);
}

.data-tag--fall {
  background: var(--color-fall-bg);
  color: var(--color-fall);
}

.data-tag--fall .data-tag__value {
  color: var(--color-fall);
  font-weight: var(--font-semibold);
}

.data-tag--flat {
  background: var(--color-flat-bg);
  color: var(--color-flat);
}

.data-tag--flat .data-tag__value {
  color: var(--color-flat);
  font-weight: var(--font-semibold);
}

.data-tag--primary {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.data-tag--primary .data-tag__value {
  color: var(--color-primary-600);
  font-weight: var(--font-semibold);
}

.data-tag--warning {
  background: var(--color-warning-50);
  color: var(--color-warning-600);
}

.data-tag--warning .data-tag__value {
  color: var(--color-warning-600);
  font-weight: var(--font-semibold);
}

.data-tag--danger {
  background: var(--color-danger-50);
  color: var(--color-danger-600);
}

.data-tag--danger .data-tag__value {
  color: var(--color-danger-600);
  font-weight: var(--font-semibold);
}

.data-tag__label {
  font-weight: var(--font-medium);
  color: var(--text-muted);
}

.data-tag--rise .data-tag__label,
.data-tag--fall .data-tag__label,
.data-tag--flat .data-tag__label,
.data-tag--primary .data-tag__label,
.data-tag--warning .data-tag__label,
.data-tag--danger .data-tag__label {
  color: inherit;
  opacity: 0.75;
}

.data-tag__value {
  font-family: var(--font-data);
  font-weight: var(--font-medium);
}
</style>
