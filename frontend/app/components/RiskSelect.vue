<template>
  <div class="risk-select-wrapper" ref="selectRef">
    <button
      type="button"
      class="risk-select-trigger"
      :class="{ active: isOpen }"
      @click="toggleDropdown"
    >
      <span class="risk-select-label">{{ currentLabel }}</span>
      <svg
        class="risk-select-arrow"
        :class="{ rotated: isOpen }"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
      >
        <path fill="#64748B" d="M6 8L1 3h10z" />
      </svg>
    </button>

    <Transition name="dropdown">
      <div v-if="isOpen" class="risk-select-dropdown">
        <div
          v-for="option in options"
          :key="option.value"
          class="risk-select-option"
          :class="{ selected: option.value === modelValue }"
          @click="selectOption(option.value)"
        >
          <span class="option-label">{{ option.label }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
interface Option {
  value: string
  label: string
}

interface Props {
  modelValue: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const options: Option[] = [
  { value: 'conservative', label: '保守型' },
  { value: 'neutral', label: '中性' },
  { value: 'aggressive', label: '激进型' }
]

const isOpen = ref(false)
const selectRef = ref<HTMLElement | null>(null)

const currentLabel = computed(() => {
  const option = options.find(opt => opt.value === props.modelValue)
  return option ? option.label : '中性'
})

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function selectOption(value: string) {
  emit('update:modelValue', value)
  isOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (selectRef.value && !selectRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.risk-select-wrapper {
  position: relative;
  display: inline-flex;
}

.risk-select-trigger {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 16px 16px 16px 16px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  background: transparent;
  cursor: pointer;
  outline: none;
  transition: color 0.2s;
}

.risk-select-trigger:hover {
  color: var(--primary-color);
}

.risk-select-trigger.active {
  color: var(--primary-color);
}

.risk-select-label {
  white-space: nowrap;
}

.risk-select-arrow {
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.risk-select-arrow.rotated {
  transform: rotate(180deg);
}

.risk-select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--border-color);
  z-index: 100;
  overflow: hidden;
}

.risk-select-option {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.risk-select-option:hover {
  background: #F8FAFC;
  color: var(--primary-color);
}

.risk-select-option.selected {
  background: #EFF6FF;
  color: var(--primary-color);
  font-weight: 500;
}

.option-label {
  flex: 1;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.dropdown-enter-to,
.dropdown-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>
