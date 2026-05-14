import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LLMSettings, DatasourceSettings, RAGSettings, AllSettings } from '~/services/settings'
import { settingsService } from '~/services/settings'

/* 配置管理 Store */
export const useSettingsStore = defineStore('settings', () => {
  /* ========== State ========== */

  /* LLM 配置 */
  const llm = ref<LLMSettings>({
    apiBaseUrl: '',
    apiKey: '',
    model: '',
    embeddingApiBaseUrl: '',
    embeddingApiKey: '',
    embeddingModel: '',
  })

  /* 数据源配置 */
  const datasource = ref<DatasourceSettings>({
    tushareToken: '',
  })

  /* RAG 配置 */
  const rag = ref<RAGSettings>({
    embeddingMode: 'api',
    topK: 5,
    chunkSize: 500,
    chunkOverlap: 50,
  })

  /* 加载状态 */
  const loading = ref(false)

  /* 保存状态 */
  const saving = ref(false)

  /* LLM 测试状态 */
  const testing = ref(false)

  /* LLM 测试结果 */
  const testResult = ref<{ success: boolean; message: string; latencyMs?: number } | null>(null)

  /* ========== Actions ========== */

  /* 加载所有配置 */
  async function fetchSettings() {
    loading.value = true
    try {
      const data = await settingsService.getAllSettings()
      llm.value = data.llm
      datasource.value = data.datasource
      rag.value = data.rag
    } catch (error) {
      console.error('加载配置失败:', error)
    } finally {
      loading.value = false
    }
  }

  /* 保存 LLM 配置 */
  async function saveLLMSettings() {
    saving.value = true
    try {
      const data = await settingsService.updateLLMSettings(llm.value)
      llm.value = data
      return true
    } catch (error) {
      console.error('保存 LLM 配置失败:', error)
      return false
    } finally {
      saving.value = false
    }
  }

  /* 保存数据源配置 */
  async function saveDatasourceSettings() {
    saving.value = true
    try {
      const data = await settingsService.updateDatasourceSettings(datasource.value)
      datasource.value = data
      return true
    } catch (error) {
      console.error('保存数据源配置失败:', error)
      return false
    } finally {
      saving.value = false
    }
  }

  /* 测试 LLM 连接 */
  async function testConnection() {
    testing.value = true
    testResult.value = null
    try {
      const result = await settingsService.testLLMConnection({
        apiBaseUrl: llm.value.apiBaseUrl,
        apiKey: llm.value.apiKey,
        model: llm.value.model,
      })
      testResult.value = result
    } catch (error: any) {
      testResult.value = {
        success: false,
        message: error?.message || '连接测试失败',
      }
    } finally {
      testing.value = false
    }
  }

  return {
    /* State */
    llm,
    datasource,
    rag,
    loading,
    saving,
    testing,
    testResult,
    /* Actions */
    fetchSettings,
    saveLLMSettings,
    saveDatasourceSettings,
    testConnection,
  }
})

/* 导出类型 */
export type SettingsStore = ReturnType<typeof useSettingsStore>
