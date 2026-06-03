import type { Ref } from 'vue'
import { get } from '~/services/api'

/* 基金搜索结果项接口（camelCase，与 api 客户端自动转换后的格式一致） */
export interface FundSearchItem {
  fundCode: string
  fundName: string
  fundType: string
  purchaseStatus: string
  currentScale: number
}

/* 基金搜索响应接口 */
export interface FundSearchResponse {
  total: number
  page: number
  size: number
  totalPages: number
  items: FundSearchItem[]
}

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
      /* 使用 api 客户端发起搜索请求，自动处理代理、键名转换、错误处理 */
      const data = await get<FundSearchResponse>('/funds/search', {
        keyword: keyword.trim(),
        page,
        size,
      })
      return data.items
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
