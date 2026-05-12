<template>
  <header class="workspace-header">
    <div class="header-left">
      <NuxtLink to="/" class="header-logo">
        <span class="logo-text">FundAI</span>
      </NuxtLink>
    </div>
    <div class="header-center">
      <div class="header-search">
        <input
          :value="fundInput"
          type="text"
          placeholder="输入基金代码或名称"
          :disabled="isAnalyzing"
          @input="$emit('update:fundInput', ($event.target as HTMLInputElement).value)"
        >
        <button class="btn-search" :disabled="isAnalyzing" @click="$emit('startAnalysis')">
          {{ isAnalyzing ? '分析中...' : '分析' }}
        </button>
      </div>
    </div>
    <div class="header-right">
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
/* 工作台顶部导航栏组件 */

defineProps<{
  /* 基金输入框值 */
  fundInput: string
  /* 是否正在分析 */
  isAnalyzing: boolean
}>()

defineEmits<{
  /* 基金输入框值更新 */
  'update:fundInput': [value: string]
  /* 开始分析 */
  'startAnalysis': []
  /* 打开设置弹窗 */
  'openSettings': []
}>()
</script>

<style scoped>
.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
  min-width: 60px;
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
  color: #909399;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-settings:hover:not(:disabled) {
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
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
</style>
