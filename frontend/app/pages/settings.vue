<template>
  <div class="settings-page">
    <!-- 顶部导航栏 -->
    <header class="settings-header">
      <div class="header-left">
        <button class="btn-back" @click="goBack">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          返回工作台
        </button>
      </div>
      <h1 class="header-title">系统设置</h1>
      <div class="header-right"></div>
    </header>

    <!-- 主内容区域 -->
    <main class="settings-main">
      <!-- LLM 对话模型配置区域 -->
      <el-card class="settings-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>LLM 对话模型配置</span>
          </div>
        </template>

        <el-form label-position="top" class="settings-form">
          <!-- API Base URL 输入 -->
          <el-form-item label="API Base URL">
            <el-input
              v-model="settingsStore.llm.apiBaseUrl"
              placeholder="例如：https://api.openai.com/v1"
              class="full-width"
            />
            <div class="form-tip">
              支持 OpenAI 兼容的 API 地址，如 OpenAI、阿里云百炼、DeepSeek 等
            </div>
          </el-form-item>

          <!-- API Key 输入 -->
          <el-form-item label="API Key">
            <el-input
              v-model="settingsStore.llm.apiKey"
              type="password"
              placeholder="请输入 API Key"
              show-password
              class="full-width"
            />
          </el-form-item>

          <!-- 对话模型输入 -->
          <el-form-item label="对话模型名称">
            <el-input
              v-model="settingsStore.llm.model"
              placeholder="例如：gpt-4、qwen-plus、deepseek-chat"
              class="full-width"
            />
            <div class="form-tip">
              填写服务商支持的模型名称
            </div>
          </el-form-item>

          <!-- 操作按钮 -->
          <el-form-item class="form-actions">
            <el-button
              type="warning"
              :loading="settingsStore.testing"
              @click="handleTestConnection"
            >
              {{ settingsStore.testing ? '测试中...' : '测试连接' }}
            </el-button>
            <el-button
              type="primary"
              :loading="settingsStore.saving"
              @click="handleSaveLLM"
            >
              {{ settingsStore.saving ? '保存中...' : '保存配置' }}
            </el-button>
          </el-form-item>

          <!-- 测试结果 -->
          <div v-if="settingsStore.testResult" class="test-result" :class="settingsStore.testResult.success ? 'test-success' : 'test-failed'">
            <el-tag :type="settingsStore.testResult.success ? 'success' : 'danger'" effect="dark">
              {{ settingsStore.testResult.success ? '连接成功' : '连接失败' }}
            </el-tag>
            <span class="test-message">{{ settingsStore.testResult.message }}</span>
            <span v-if="settingsStore.testResult.latencyMs" class="test-latency">
              延迟: {{ settingsStore.testResult.latencyMs }}ms
            </span>
          </div>
        </el-form>
      </el-card>

      <!-- Embedding 模型配置区域 -->
      <el-card class="settings-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="16"></line>
              <line x1="8" y1="12" x2="16" y2="12"></line>
            </svg>
            <span>Embedding 模型配置</span>
            <span class="header-tip">（任一字段为空则不启用RAG）</span>
          </div>
        </template>

        <el-form label-position="top" class="settings-form">
          <!-- Embedding API Base URL 输入 -->
          <el-form-item label="Embedding API Base URL">
            <el-input
              v-model="settingsStore.llm.embeddingApiBaseUrl"
              placeholder="例如：https://api.openai.com/v1"
              class="full-width"
            />
            <div class="form-tip">
              可与对话模型使用相同的 API 地址，或单独配置
            </div>
          </el-form-item>

          <!-- Embedding API Key 输入 -->
          <el-form-item label="Embedding API Key">
            <el-input
              v-model="settingsStore.llm.embeddingApiKey"
              type="password"
              placeholder="请输入 Embedding API Key"
              show-password
              class="full-width"
            />
          </el-form-item>

          <!-- Embedding 模型输入 -->
          <el-form-item label="Embedding 模型名称">
            <el-select
              v-model="settingsStore.llm.embeddingModel"
              placeholder="请选择或输入 Embedding 模型"
              class="full-width"
              filterable
              allow-create
            >
              <el-option label="text-embedding-v4 (推荐，Qwen3-Embedding)" value="text-embedding-v4" />
              <el-option label="text-embedding-v3" value="text-embedding-v3" />
              <el-option label="text-embedding-v2" value="text-embedding-v2" />
              <el-option label="text-embedding-v1" value="text-embedding-v1" />
            </el-select>
            <div class="form-tip form-tip-warning">
              <strong>重要提示：</strong>请选择 Embedding 模型，不要选择 Rerank 模型（如 gte-rerank-v2）。Rerank 模型用于搜索结果重排序，不支持文本向量化。
            </div>
          </el-form-item>

          <!-- 保存按钮 -->
          <el-form-item class="form-actions">
            <el-button
              type="primary"
              :loading="settingsStore.saving"
              @click="handleSaveLLM"
            >
              {{ settingsStore.saving ? '保存中...' : '保存配置' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 数据源配置区域 -->
      <el-card class="settings-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            <span>数据源配置</span>
          </div>
        </template>

        <el-form label-position="top" class="settings-form">
          <!-- Tushare Token -->
          <el-form-item label="Tushare Token">
            <el-input
              v-model="settingsStore.datasource.tushareToken"
              type="password"
              placeholder="请输入 Tushare Token"
              show-password
              class="full-width"
            />
            <div class="form-tip">
              用于获取基金净值、持仓等数据，可在
              <a href="https://tushare.pro" target="_blank" rel="noopener">tushare.pro</a>
              注册获取
            </div>
          </el-form-item>

          <!-- 保存按钮 -->
          <el-form-item class="form-actions">
            <el-button
              type="primary"
              :loading="settingsStore.saving"
              @click="handleSaveDatasource"
            >
              {{ settingsStore.saving ? '保存中...' : '保存配置' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- RAG 配置区域 -->
      <el-card class="settings-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>RAG 检索增强配置</span>
          </div>
        </template>

        <el-form label-position="top" class="settings-form">
          <!-- Embedding 模式 -->
          <el-form-item label="Embedding 模式">
            <el-select v-model="settingsStore.rag.embeddingMode" placeholder="选择 Embedding 模式" class="full-width">
              <el-option label="远程 API" value="api" />
              <el-option label="本地模型" value="local" />
            </el-select>
          </el-form-item>

          <!-- Top K -->
          <el-form-item label="Top K（检索返回数量）">
            <el-input-number
              v-model="settingsStore.rag.topK"
              :min="1"
              :max="20"
              :step="1"
              class="full-width"
            />
          </el-form-item>

          <!-- Chunk Size -->
          <el-form-item label="Chunk Size（分块大小）">
            <el-input-number
              v-model="settingsStore.rag.chunkSize"
              :min="100"
              :max="2000"
              :step="100"
              class="full-width"
            />
          </el-form-item>

          <!-- Chunk Overlap -->
          <el-form-item label="Chunk Overlap（分块重叠）">
            <el-input-number
              v-model="settingsStore.rag.chunkOverlap"
              :min="0"
              :max="500"
              :step="10"
              class="full-width"
            />
          </el-form-item>

          <!-- 保存按钮 -->
          <el-form-item class="form-actions">
            <el-button type="primary" @click="handleSaveRAG">
              保存配置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 关于信息 -->
      <div class="about-section">
        <el-divider>关于</el-divider>
        <div class="about-content">
          <div class="about-item">
            <span class="about-label">版本</span>
            <span class="about-value">v0.1.0</span>
          </div>
          <div class="about-item">
            <span class="about-label">项目地址</span>
            <a
              class="about-link"
              href="https://github.com"
              target="_blank"
              rel="noopener"
            >
              GitHub
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </a>
          </div>
          <div class="about-disclaimer">
            免责声明：本系统提供的分析结论仅供用户参考，不作为投资决策的唯一依据。基金投资有风险，入市需谨慎。
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
/* 设置页面 - 配置 LLM、数据源、RAG 参数 */

import { ElMessage } from 'element-plus'
import { useSettingsStore } from '~/stores/settings'

const router = useRouter()
const settingsStore = useSettingsStore()

/* 返回工作台 */
function goBack() {
  router.push('/workspace')
}

/* 保存 LLM 配置 */
async function handleSaveLLM() {
  const success = await settingsStore.saveLLMSettings()
  if (success) {
    ElMessage.success('LLM 配置保存成功')
  } else {
    ElMessage.error('LLM 配置保存失败')
  }
}

/* 保存数据源配置 */
async function handleSaveDatasource() {
  const success = await settingsStore.saveDatasourceSettings()
  if (success) {
    ElMessage.success('数据源配置保存成功')
  } else {
    ElMessage.error('数据源配置保存失败')
  }
}

/* 测试 LLM 连接 */
async function handleTestConnection() {
  await settingsStore.testConnection()
  if (settingsStore.testResult?.success) {
    ElMessage.success('连接测试成功')
  } else {
    ElMessage.error(settingsStore.testResult?.message || '连接测试失败')
  }
}

/* 保存 RAG 配置（暂时只保存到前端 store，后续再对接后端 API） */
function handleSaveRAG() {
  ElMessage.success('RAG 配置已保存（仅前端）')
}

/* 页面加载时自动获取配置 */
onMounted(() => {
  settingsStore.fetchSettings()
})
</script>

<style scoped>
/* 设置页面容器 */
.settings-page {
  min-height: 100vh;
  background: var(--bg-secondary, #F8FAFC);
  display: flex;
  flex-direction: column;
}

/* 顶部导航栏 */
.settings-header {
  height: 56px;
  background: white;
  border-bottom: 1px solid var(--border-color, #E2E8F0);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  width: 160px;
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #0F172A);
}

.header-right {
  width: 160px;
}

/* 返回按钮 */
.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  color: var(--text-secondary, #475569);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-back:hover {
  color: var(--primary-color, #3B82F6);
  background: var(--bg-secondary, #F8FAFC);
}

/* 主内容区域 */
.settings-main {
  flex: 1;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

/* 配置卡片 */
.settings-card {
  margin-bottom: 24px;
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E8F0);
}

.settings-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color, #E2E8F0);
  background: var(--bg-secondary, #F8FAFC);
}

.settings-card :deep(.el-card__body) {
  padding: 24px;
}

/* 卡片标题 */
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #0F172A);
}

.card-header svg {
  color: var(--primary-color, #3B82F6);
  flex-shrink: 0;
}

.header-tip {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted, #94A3B8);
  margin-left: 8px;
}

/* 表单样式 */
.settings-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-primary, #0F172A);
}

.settings-form :deep(.el-input__wrapper),
.settings-form :deep(.el-select__wrapper) {
  border-radius: 8px;
}

/* 全宽控件 */
.full-width {
  width: 100%;
}

/* 表单提示 */
.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted, #94A3B8);
  line-height: 1.5;
}

.form-tip a {
  color: var(--primary-color, #3B82F6);
  text-decoration: none;
}

.form-tip a:hover {
  text-decoration: underline;
}

.form-tip-warning {
  margin-top: 8px;
  padding: 10px 12px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  color: #d48806;
}

.form-tip-warning strong {
  color: #ad6800;
}

/* 操作按钮区域 */
.form-actions {
  margin-top: 8px;
  margin-bottom: 0;
}

.form-actions :deep(.el-form-item__content) {
  display: flex;
  gap: 12px;
}

/* 测试结果 */
.test-result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-top: 4px;
}

.test-success {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
}

.test-failed {
  background: #fef0f0;
  border: 1px solid #fde2e2;
}

.test-message {
  font-size: 13px;
  color: var(--text-secondary, #475569);
}

.test-latency {
  font-size: 12px;
  color: var(--text-muted, #94A3B8);
  font-family: monospace;
}

/* 关于区域 */
.about-section {
  margin-top: 16px;
}

.about-section :deep(.el-divider__text) {
  color: var(--text-muted, #94A3B8);
  font-size: 13px;
}

.about-content {
  padding: 0 8px;
}

.about-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color, #E2E8F0);
}

.about-item:last-of-type {
  border-bottom: none;
}

.about-label {
  font-size: 14px;
  color: var(--text-secondary, #475569);
}

.about-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #0F172A);
}

.about-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--primary-color, #3B82F6);
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.2s;
}

.about-link:hover {
  opacity: 0.8;
}

.about-disclaimer {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--bg-tertiary, #F1F5F9);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted, #94A3B8);
  line-height: 1.6;
}

/* 响应式 */
@media (max-width: 768px) {
  .settings-main {
    padding: 20px 16px 48px;
  }

  .settings-header {
    padding: 0 16px;
  }

  .header-title {
    font-size: 16px;
  }
}
</style>
