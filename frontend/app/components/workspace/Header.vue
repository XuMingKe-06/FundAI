<template>
  <header class="workspace-header">
    <div class="header-left">
      <NuxtLink to="/" class="header-logo">
        <span class="logo-text">FundAI</span>
      </NuxtLink>
    </div>
    <div class="header-center">
      <div class="header-search" ref="searchBarRef">
        <input
          :value="fundInput"
          type="text"
          placeholder="输入基金代码或名称"
          :disabled="isAnalyzing"
          @input="onInput($event)"
          @focus="onFocus"
        >
        <button class="btn-search" :disabled="isAnalyzing" @click="$emit('startAnalysis')">
          {{ isAnalyzing ? '分析中...' : '分析' }}
        </button>
        <div v-if="showSuggestions && suggestionItems.length > 0" class="search-suggestions">
          <div
            v-for="item in suggestionItems"
            :key="item.fundCode"
            class="suggestion-item"
            @mousedown.prevent="selectFund(item.fundCode, item.fundName)"
          >
            <span class="suggestion-code">{{ item.fundCode }}</span>
            <span class="suggestion-name">{{ item.fundName }}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="header-right">
      <ThemeToggle />
      <button
        class="btn-settings"
        :disabled="isAnalyzing"
        title="分析设置"
        @click="$emit('openSettings')"
      >
        <svg
          class="settings-icon"
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useFundService, type FundSearchItem } from '~/composables/useFundService'

defineProps<{
  fundInput: string
  isAnalyzing: boolean
}>()

const emit = defineEmits<{
  'update:fundInput': [value: string]
  'startAnalysis': []
  'openSettings': []
}>()

const fundService = useFundService()
const showSuggestions = ref(false)
const suggestionItems = ref<FundSearchItem[]>([])
const searchBarRef = ref<HTMLElement | null>(null)

function onInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  emit('update:fundInput', value)
  const keyword = value.trim()
  if (keyword.length > 0) {
    fundService.debouncedSearchFunds(keyword, (results) => {
      suggestionItems.value = results
      showSuggestions.value = results.length > 0
    })
  } else {
    showSuggestions.value = false
    suggestionItems.value = []
  }
}

function onFocus() {
  if (suggestionItems.value.length > 0) {
    showSuggestions.value = true
  }
}

function selectFund(code: string, name: string) {
  emit('update:fundInput', code + ' - ' + name)
  showSuggestions.value = false
  suggestionItems.value = []
}

function handleClickOutside(event: MouseEvent) {
  if (searchBarRef.value && !searchBarRef.value.contains(event.target as Node)) {
    showSuggestions.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  fundService.cleanup()
})
</script>

<style scoped>
.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
  min-width: 60px;
  gap: var(--space-1);
}

.btn-settings {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-settings:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary-500);
}

.btn-settings:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.settings-icon {
  display: block;
  transition: transform 0.4s ease;
}

.btn-settings:hover:not(:disabled) .settings-icon {
  transform: rotate(60deg);
}

.search-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 60px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown);
  max-height: 240px;
  overflow-y: auto;
  transition: background-color var(--transition-base), border-color var(--transition-base);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.suggestion-item:hover {
  background: var(--bg-hover);
}

.suggestion-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.suggestion-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
