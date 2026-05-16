<template>
  <el-dialog
    v-model="showSettings"
    title="分析设置"
    width="480px"
    :close-on-click-modal="true"
  >
    <el-form label-position="top">
      <el-form-item label="智能体执行模式">
        <el-radio-group :model-value="analysisMode" @change="(val: string | number | boolean) => $emit('modeChange', val as AnalysisMode)">
          <el-radio value="parallel" class="settings-radio">
            <div class="settings-radio-content">
              <span class="settings-radio-title">并行模式</span>
              <span class="settings-radio-desc">所有分析智能体同时运行，分析速度更快，适合快速获取初步结论</span>
            </div>
          </el-radio>
          <el-radio value="sequential" class="settings-radio">
            <div class="settings-radio-content">
              <span class="settings-radio-title">串行模式</span>
              <span class="settings-radio-desc">智能体按顺序逐个分析，每个智能体可参考前序分析结果，结论更深入</span>
            </div>
          </el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <div class="settings-mode-note">
      <p v-if="analysisMode === 'parallel'">
        当前所有5个分析智能体同时运行，决策智能体等所有分析完成后汇总结果。
        适合快速获取初步投资参考。
      </p>
      <p v-else>
        智能体按 <strong>基本面 → 技术面 → 风险 → 成本 → 情绪</strong> 顺序依次分析，
        每个智能体可参考前序分析结果，推理更连贯但耗时较长。
      </p>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
/* 工作台分析设置弹窗组件 */

import type { AnalysisMode } from '~/composables/useAnalysisSettings'

/* 使用 defineModel 实现 v-model:show-settings 双向绑定 */
const showSettings = defineModel<boolean>('showSettings', { required: true })

defineProps<{
  /* 当前分析模式 */
  analysisMode: AnalysisMode
}>()

defineEmits<{
  /* 分析模式变更 */
  'modeChange': [mode: AnalysisMode]
}>()
</script>

<style scoped>
:deep(.el-radio-group) {
  display: flex;
  flex-direction: column;
  width: 100%;
  align-items: stretch;
}

:deep(.settings-radio) {
  display: flex;
  align-items: flex-start;
  height: auto !important;
  margin-right: 0 !important;
  margin-bottom: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-md);
  white-space: normal;
  width: 100%;
  box-sizing: border-box;
  transition: all var(--transition-fast);
}

:deep(.settings-radio.is-checked) {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

:deep(.settings-radio:hover) {
  border-color: var(--color-primary-300);
}

:deep(.settings-radio .el-radio__label) {
  width: 100%;
}

.settings-radio-content {
  display: flex;
  flex-direction: column;
  margin-left: 8px;
  width: 100%;
}

.settings-radio-title {
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.settings-radio-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  line-height: var(--leading-normal);
}

.settings-mode-note {
  margin-top: var(--space-1);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.settings-mode-note strong {
  color: var(--color-primary-500);
}
</style>
