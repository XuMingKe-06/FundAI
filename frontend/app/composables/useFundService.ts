import type { Ref } from 'vue'
import type { ApiResponse } from '~/services/api'

/* 基金搜索结果项接口 */
export interface FundSearchItem {
  fund_code: string
  fund_name: string
  fund_type: string
  purchase_status: string
  current_scale: number
}

/* 基金搜索响应接口 */
export interface FundSearchResponse {
  total: number
  page: number
  size: number
  total_pages: number
  items: FundSearchItem[]
}

/* API 基础 URL */
const API_BASE_URL = 'http://localhost:8000/api/v1'

/* 基金服务 composable */
export const useFundService = () => {
  /* 搜索加载状态 */
  const isSearching: Ref<boolean> = ref(false)

  /* 搜索错误信息 */
  const searchError: Ref<string | null> = ref(null)

  /* 搜索防抖定时器 */
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

  /* 搜索基金 */
  const searchFunds = async (keyword: string, page: number = 1, size: number = 10): Promise<FundSearchItem[]> => {
    /* 清除之前的错误 */
    searchError.value = null

    /* 如果关键词为空，返回空数组 */
    if (!keyword.trim()) {
      return []
    }

    isSearching.value = true

    try {
      /* 获取 token */
      const token = localStorage.getItem('access_token')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }

      /* 如果有 token，添加到请求头 */
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      /* 发送搜索请求 */
      const response = await fetch(
        `${API_BASE_URL}/funds/search?keyword=${encodeURIComponent(keyword.trim())}&page=${page}&size=${size}`,
        {
          method: 'GET',
          headers
        }
      )

      /* 解析响应 */
      const result: ApiResponse<FundSearchResponse> = await response.json()

      /* 检查响应状态 */
      if (result.code !== 200) {
        throw new Error(result.message || '搜索失败')
      }

      return result.data.items
    } catch (error) {
      /* 记录错误信息 */
      searchError.value = error instanceof Error ? error.message : '搜索失败，请稍后重试'
      console.error('基金搜索失败:', error)
      return []
    } finally {
      isSearching.value = false
    }
  }

  /* 防抖搜索基金 */
  const debouncedSearchFunds = (keyword: string, callback: (results: FundSearchItem[]) => void, delay: number = 300): void => {
    /* 清除之前的定时器 */
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer)
    }

    /* 设置新的定时器 */
    searchDebounceTimer = setTimeout(async () => {
      const results = await searchFunds(keyword)
      callback(results)
    }, delay)
  }

  /* 清理定时器 */
  const cleanup = (): void => {
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer)
      searchDebounceTimer = null
    }
  }

  return {
    isSearching: readonly(isSearching),
    searchError: readonly(searchError),
    searchFunds,
    debouncedSearchFunds,
    cleanup
  }
}
