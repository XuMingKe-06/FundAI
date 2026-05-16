<template>
  <div class="agent-thinking-container">
    <!-- 智能体头部 -->
    <div class="agent-header">
      <h2>{{ agentData?.name }}</h2>
      <span class="agent-status-badge" :class="agentData?.status">{{ getAgentStatusText(agentData?.status || '') }}</span>
    </div>

    <!-- 工作流程区域 -->
    <div class="workflow-area">
      <div class="workflow-timeline">
        <!-- 遍历 thinking 数组，根据 type 渲染不同类型的内容 -->
        <template v-for="(step, index) in agentData?.thinking" :key="step.id || `step-${index}`">
          <div
            v-if="step.text?.trim() || step.toolName"
            class="workflow-item"
            :class="step.type || 'legacy'"
          >
            <!-- 状态提示（如"开始分析"、"调用LLM"） -->
            <div v-if="step.type === 'status'" class="status-item">
              <span class="timeline-dot"></span>
              <span class="status-text">{{ step.text }}</span>
            </div>

            <!-- 普通思考内容（浅色小字） -->
            <div v-else-if="step.type === 'thinking'" class="thinking-item">
              <span class="timeline-dot"></span>
              <div class="thinking-content thinking-normal md-content md-thinking">
                <span class="thinking-text" v-html="renderMarkdown(step.text)"></span>
              </div>
            </div>

            <!-- 深度思考内容（Thinking...折叠标签） -->
            <div v-else-if="step.type === 'deep_thinking'" class="thinking-item">
              <span class="timeline-dot deep"></span>
              <details class="thinking-content thinking-deep" :open="step.isStreaming">
                <summary class="thinking-summary">
                  <span class="thinking-label">Thinking...</span>
                </summary>
                <div class="thinking-detail md-content md-thinking" v-html="renderMarkdown(step.deepThinkingContent || step.text)">
                </div>
              </details>
            </div>

            <!-- 工具调用 -->
            <div v-else-if="step.type === 'tool_call'" class="tool-call-item">
              <span class="timeline-dot tool"></span>
              <div class="tool-call-content">
                <div class="tool-name">
                  <span class="tool-icon">[T]</span>
                  <span>{{ step.toolChineseName || step.toolName || step.text }}</span>
                </div>
                <span class="tool-status" :class="step.toolStatus">{{ getToolStatusText(step.toolStatus) }}</span>
              </div>
              <!-- 工具结果展示 -->
              <div v-if="step.toolResultText" class="tool-result-display">
                <span class="tool-result-label">结果：</span>
                <span class="tool-result-value">{{ step.toolResultText }}</span>
              </div>
            </div>

            <!-- 兼容旧格式数据（没有 type 字段） -->
            <div v-else-if="step.text && step.text.trim()" class="thinking-item">
              <span class="timeline-dot"></span>
              <div class="thinking-content thinking-normal md-content md-thinking">
                <span class="thinking-text" v-html="renderMarkdown(step.text)"></span>
              </div>
            </div>
          </div>
        </template>

        <!-- Thinking... 动态指示器 - 位于链条下方，随链条延伸移动 -->
        <div v-if="showThinkingIndicator && !isPaused" class="workflow-item thinking-indicator-wrapper">
          <span class="timeline-dot thinking"></span>
          <ThinkingIndicator :visible="true" />
        </div>
        <!-- 暂停状态静态指示器 -->
        <div v-if="showThinkingIndicator && isPaused" class="workflow-item thinking-indicator-wrapper">
          <span class="timeline-dot paused"></span>
          <span class="paused-text">Paused</span>
        </div>
      </div>
    </div>

    <!-- 分析结果区域（如果有） -->
    <div class="agent-result" v-if="agentData?.result">
      <h3>分析结果</h3>
      <div class="result-content md-content" v-html="renderMarkdown(agentData.result)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 工作台智能体思考过程视图组件 */

import { getAgentStatusText, getToolStatusText } from '~/utils/format'
import { renderMarkdown } from '~/utils/markdown'
import type { AgentInfo } from '~/stores/agent'

defineProps<{
  /* 当前智能体数据 */
  agentData: AgentInfo | null
  /* 是否显示 Thinking... 指示器 */
  showThinkingIndicator: boolean
  /* 分析是否暂停 */
  isPaused: boolean
}>()
</script>

<style scoped>
@import '~/assets/css/markdown.css';

.agent-thinking-container {
  width: 100%;
  padding: 24px;
  text-align: left;
}

.agent-thinking-container > .agent-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.agent-thinking-container > .agent-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
  text-align: left;
  flex: 0 0 auto;
}

.agent-status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.agent-status-badge.pending {
  background: #f0f0f0;
  color: #909399;
}

.agent-status-badge.running {
  background: #ecf5ff;
  color: #409EFF;
}

.agent-status-badge.completed {
  background: #f0f9eb;
  color: #67C23A;
}

.agent-status-badge.error {
  background: #fef0f0;
  color: #F56C6C;
}

.workflow-area {
  margin-bottom: 24px;
}

.workflow-timeline {
  position: relative;
  padding-left: 24px;
}

.workflow-timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e0e0e0;
}

.workflow-item {
  position: relative;
  margin-bottom: 16px;
}

.timeline-dot {
  position: absolute;
  left: -21px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #409EFF;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #e0e0e0;
}

.timeline-dot.deep {
  background: #909399;
}

.timeline-dot.tool {
  background: #E6A23C;
}

.timeline-dot.thinking {
  background: #909399;
  animation: thinking-pulse 1.5s ease-in-out infinite;
}

.timeline-dot.paused {
  background: #E6A23C;
  box-shadow: 0 0 0 2px #e0e0e0;
}

.paused-text {
  font-size: 14px;
  font-weight: 500;
  font-style: italic;
  color: #E6A23C;
  letter-spacing: 1px;
}

@keyframes thinking-pulse {
  0%, 100% { box-shadow: 0 0 0 2px #e0e0e0; }
  50% { box-shadow: 0 0 0 2px #e0e0e0, 0 0 6px 2px rgba(144, 147, 153, 0.3); }
}

.thinking-indicator-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-text {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.thinking-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.thinking-content {
  flex: 1;
}

.thinking-normal {
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.thinking-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.thinking-deep {
  margin-left: 0;
}

.thinking-deep details {
  background: #f4f4f5;
  border-radius: 6px;
  overflow: hidden;
}

.thinking-summary {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #909399;
  font-weight: 500;
  list-style: none;
  user-select: none;
}

.thinking-summary::-webkit-details-marker {
  display: none;
}

.thinking-summary::before {
  content: '>';
  display: inline-block;
  margin-right: 6px;
  font-weight: bold;
  transition: transform 0.2s;
}

details[open] .thinking-summary::before {
  transform: rotate(90deg);
}

.thinking-label {
  font-style: italic;
}

.thinking-detail {
  padding: 0 12px 12px;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
  white-space: normal;
  word-break: break-word;
}

.thinking-detail p {
  margin: 0.2em 0;
}

.tool-call-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-call-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 6px;
  flex: 1;
}

.tool-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #303133;
}

.tool-icon {
  color: #E6A23C;
  font-weight: bold;
}

.tool-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.tool-status.pending {
  background: #ecf5ff;
  color: #409EFF;
}

.tool-status.success,
.tool-status.completed {
  background: #f0f9eb;
  color: #67C23A;
}

.tool-status.failed {
  background: #fef0f0;
  color: #F56C6C;
}

.tool-result-display {
  margin-top: 6px;
  padding: 6px 10px;
  background: #f0f9eb;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  border-left: 3px solid #67C23A;
}

.tool-result-label {
  color: #909399;
  font-weight: 500;
}

.tool-result-value {
  color: #303133;
}

.agent-result {
  margin-top: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  border-left: 4px solid #409EFF;
}

.agent-result h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #303133;
}

.result-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}
</style>
