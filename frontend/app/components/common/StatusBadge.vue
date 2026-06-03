<template>
  <span class="status-badge" :class="[`status-badge--${status}`, `status-badge--${size}`]">
    <span class="status-badge__dot"></span>
    <span v-if="text" class="status-badge__text">{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  status: 'pending' | 'running' | 'completed' | 'error'
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

withDefaults(defineProps<Props>(), {
  size: 'md',
  text: ''
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.status-badge--sm {
  padding: 2px var(--space-2);
  font-size: var(--text-xs);
}

.status-badge--md {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
}

.status-badge--lg {
  padding: var(--space-1) var(--space-4);
  font-size: var(--text-base);
}

.status-badge__dot {
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.status-badge--sm .status-badge__dot {
  width: 6px;
  height: 6px;
}

.status-badge--md .status-badge__dot {
  width: 8px;
  height: 8px;
}

.status-badge--lg .status-badge__dot {
  width: 10px;
  height: 10px;
}

.status-badge--pending {
  background: var(--color-gray-100);
  color: var(--color-gray-500);
}

.status-badge--pending .status-badge__dot {
  background: var(--color-gray-400);
}

.status-badge--running {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.status-badge--running .status-badge__dot {
  background: var(--color-primary-500);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-badge--completed {
  background: var(--color-success-50);
  color: var(--color-success-600);
}

.status-badge--completed .status-badge__dot {
  background: var(--color-success-500);
}

.status-badge--error {
  background: var(--color-danger-50);
  color: var(--color-danger-600);
}

.status-badge--error .status-badge__dot {
  background: var(--color-danger-500);
}

.status-badge__text {
  font-weight: var(--font-medium);
  line-height: var(--leading-normal);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
</style>
