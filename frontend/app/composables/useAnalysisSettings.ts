/**
 * 分析设置组合式函数
 *
 * 管理分析模式（并行/串行）的读写与 localStorage 持久化
 * 支持 SSR 安全：仅在客户端环境读写 localStorage
 */

export type AnalysisMode = 'parallel' | 'sequential'

const STORAGE_KEY = 'fundai_analysis_mode'

export function useAnalysisSettings() {
  /* 当前分析模式，默认并行 */
  const analysisMode = ref<AnalysisMode>('parallel')

  /* 是否显示设置弹窗 */
  const showSettings = ref(false)

  /** 从 localStorage 加载偏好设置 */
  function loadSettings(): void {
    if (import.meta.client) {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved === 'parallel' || saved === 'sequential') {
        analysisMode.value = saved
      }
    }
  }

  /** 保存偏好设置到 localStorage */
  function saveMode(mode: AnalysisMode): void {
    analysisMode.value = mode
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, mode)
    }
  }

  /** 切换分析模式 */
  function toggleMode(): void {
    saveMode(analysisMode.value === 'parallel' ? 'sequential' : 'parallel')
  }

  /* 初始化时自动加载 */
  loadSettings()

  return {
    /** 当前分析模式 */
    analysisMode: readonly(analysisMode),
    /** 设置弹窗显示状态 */
    showSettings,
    /** 从 localStorage 加载偏好 */
    loadSettings,
    /** 保存并应用新模式 */
    saveMode,
    /** 快速切换模式 */
    toggleMode,
  }
}
