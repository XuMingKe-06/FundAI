/* SSE 事件数据接口 */
interface SSEEventData {
  type: string
  data: any
  timestamp: number
}

/* SSE 事件回调函数类型 */
type SSEEventCallback = (data: any) => void

/* SSE 配置接口 */
interface SSEConfig {
  maxReconnectAttempts: number
  baseReconnectDelay: number
  timeout: number
}

/* 默认配置 */
const DEFAULT_CONFIG: SSEConfig = {
  maxReconnectAttempts: 5,
  baseReconnectDelay: 1000,
  timeout: 30000
}

/* 支持的事件类型 */
export type SSEEventType = 'agent_status' | 'thinking' | 'agent_complete' | 'analysis_complete' | 'error' | 'result' | 'llm_thinking_stream' | 'tool_call' | 'agent_snapshot'

/* SSE 流式数据接收 composable */
export function useSSE(config: Partial<SSEConfig> = {}) {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config }

  /* 响应式状态 */
  const isConnected = ref(false)
  const error = ref<string | null>(null)
  const lastEvent = ref<SSEEventData | null>(null)

  /* 内部状态 */
  let eventSource: EventSource | null = null
  let reconnectAttempts = 0
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  let connectionTimeout: ReturnType<typeof setTimeout> | null = null
  let currentUrl: string = ''
  let streamEnded: boolean = false

  /* 事件处理器映射 */
  const eventHandlers = new Map<string, Set<SSEEventCallback>>()

  /* 计算重连延迟（指数退避：1s, 2s, 4s, 8s, 16s） */
  const getReconnectDelay = (): number => {
    return mergedConfig.baseReconnectDelay * Math.pow(2, reconnectAttempts)
  }

  /* 清除所有定时器 */
  const clearAllTimers = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
    if (connectionTimeout) {
      clearTimeout(connectionTimeout)
      connectionTimeout = null
    }
  }

  /* 触发事件处理器 */
  const emitEvent = (eventType: string, data: any) => {
    const handlers = eventHandlers.get(eventType)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (err) {
          console.error(`[SSE] 事件处理器执行错误: ${eventType}`, err)
        }
      })
    }

    /* 更新最后接收到的事件 */
    lastEvent.value = {
      type: eventType,
      data,
      timestamp: Date.now()
    }
  }

  /* 解析 SSE 事件数据 */
  const parseEventData = (data: string): any => {
    try {
      return JSON.parse(data)
    } catch {
      return data
    }
  }

  /* 处理连接错误 */
  const handleConnectionError = (errorMessage: string) => {
    /* 如果流已正常结束，不再重连 */
    if (streamEnded) {
      console.log('[SSE] 流已正常结束，不再重连')
      return
    }

    error.value = errorMessage
    isConnected.value = false
    emitEvent('error', { message: errorMessage, timestamp: Date.now() })

    /* 尝试重连 */
    if (reconnectAttempts < mergedConfig.maxReconnectAttempts) {
      const delay = getReconnectDelay()
      console.log(`[SSE] 将在 ${delay}ms 后尝试重连 (${reconnectAttempts + 1}/${mergedConfig.maxReconnectAttempts})`)

      reconnectTimeout = setTimeout(() => {
        reconnectAttempts++
        connect(currentUrl)
      }, delay)
    } else {
      console.error('[SSE] 已达到最大重连次数，停止重连')
      error.value = '连接失败，已达到最大重连次数'
    }
  }

  /* 设置连接超时 */
  const setConnectionTimeout = () => {
    clearAllTimers()
    connectionTimeout = setTimeout(() => {
      if (!isConnected.value) {
        console.error('[SSE] 连接超时')
        disconnect()
        handleConnectionError('连接超时')
      }
    }, mergedConfig.timeout)
  }

  /* 建立 SSE 连接 */
  const connect = (url: string): void => {
    /* 如果已有连接，先断开 */
    if (eventSource) {
      disconnect()
    }

    currentUrl = url
    error.value = null
    setConnectionTimeout()

    try {
      eventSource = new EventSource(url)

      /* 连接成功 */
      eventSource.onopen = () => {
        console.log('[SSE] 连接已建立')
        clearAllTimers()
        isConnected.value = true
        reconnectAttempts = 0
        error.value = null
      }

      /* 连接错误 */
      eventSource.onerror = (event) => {
        console.error('[SSE] 连接错误', event)

        if (eventSource) {
          eventSource.close()
          eventSource = null
        }

        isConnected.value = false

        /* 检查是否是服务器主动关闭 */
        if ((event as any).status === 204) {
          console.log('[SSE] 服务器主动关闭连接')
          error.value = null
          return
        }

        handleConnectionError('连接错误')
      }

      /* 处理默认消息事件 */
      eventSource.onmessage = (event) => {
        try {
          const data = parseEventData(event.data)
          emitEvent('message', data)
        } catch (err) {
          console.error('[SSE] 消息解析错误', err)
          emitEvent('error', { message: '消息解析错误', raw: event.data })
        }
      }

      /* 注册自定义事件类型处理器 */
      const eventTypes: SSEEventType[] = ['agent_status', 'thinking', 'llm_thinking_stream', 'tool_call', 'agent_complete', 'analysis_complete', 'error', 'result', 'agent_snapshot']

      eventTypes.forEach(eventType => {
        if (eventSource) {
          eventSource.addEventListener(eventType, (event: MessageEvent) => {
            try {
              const data = parseEventData(event.data)
              emitEvent(eventType, data)
            } catch (err) {
              console.error(`[SSE] 事件解析错误: ${eventType}`, err)
              emitEvent('error', { message: `事件解析错误: ${eventType}`, raw: event.data })
            }
          })
        }
      })

    } catch (err) {
      console.error('[SSE] 创建连接失败', err)
      handleConnectionError('创建连接失败')
    }
  }

  /* 断开 SSE 连接 */
  const disconnect = (): void => {
    clearAllTimers()

    if (eventSource) {
      eventSource.close()
      eventSource = null
      console.log('[SSE] 连接已断开')
    }

    isConnected.value = false
    reconnectAttempts = 0
    streamEnded = false
    currentUrl = ''
  }

  /* 标记 SSE 流已正常结束 */
  const markStreamEnded = (): void => {
    streamEnded = true
    console.log('[SSE] 流标记为正常结束')
  }

  /* 注册事件处理器 */
  const on = (eventType: string, callback: SSEEventCallback): void => {
    if (!eventHandlers.has(eventType)) {
      eventHandlers.set(eventType, new Set())
    }
    eventHandlers.get(eventType)!.add(callback)
  }

  /* 移除事件处理器 */
  const off = (eventType: string, callback?: SSEEventCallback): void => {
    if (!eventHandlers.has(eventType)) return

    if (callback) {
      eventHandlers.get(eventType)!.delete(callback)
    } else {
      /* 如果没有提供回调函数，移除该事件类型的所有处理器 */
      eventHandlers.delete(eventType)
    }
  }

  /* 手动重连 */
  const reconnect = (): void => {
    if (currentUrl) {
      reconnectAttempts = 0
      connect(currentUrl)
    }
  }

  /* 重置状态 */
  const reset = (): void => {
    disconnect()
    error.value = null
    lastEvent.value = null
    eventHandlers.clear()
  }

  /* 组件卸载时自动清理 */
  onUnmounted(() => {
    disconnect()
  })

  return {
    /* 响应式状态 */
    isConnected,
    error,
    lastEvent,

    /* 方法 */
    connect,
    disconnect,
    markStreamEnded,
    on,
    off,
    reconnect,
    reset
  }
}

export type UseSSEReturn = ReturnType<typeof useSSE>
