import { defineEventHandler, getRequestURL, getRequestHeaders, sendStream, readRawBody } from 'h3'

/* 后端服务基础地址，可通过环境变量 BACKEND_URL 覆盖 */
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export default defineEventHandler(async (event) => {
  /*
   * 使用 getRequestURL 保留查询参数（如 SSE 端点的 ?token=xxx）
   * 避免因 event.path 可能不带查询字符串导致后端认证失败
   */
  const requestURL = getRequestURL(event)
  const target = `${BACKEND_URL}${requestURL.pathname}${requestURL.search}`

  try {
    /**
     * 手动代理请求并流式转发响应。
     *
     * 不直接使用 h3 的 proxyRequest/sendProxy，因为其内部使用
     * "for await (const chunk of response.body)" 逐块转发。
     * 对于 SSE 流式响应，sendStream 基于 pipeTo/pipe 的流式管道
     * 方案兼容性更好（Web Streams API 在 Node.js 18+ 各小版本
     * 行为有差异）。
     */
    const fetchHeaders = getRequestHeaders(event)

    // 非 GET/HEAD 请求传递请求体
    let fetchBody: BodyInit | undefined
    if (event.method !== 'GET' && event.method !== 'HEAD') {
      fetchBody = await readRawBody(event, false).catch(() => undefined)
    }

    const response = await fetch(target, {
      method: event.method,
      headers: fetchHeaders,
      body: fetchBody,
    } as RequestInit)

    // 回写状态码和状态消息
    event.node.res.statusCode = response.status
    event.node.res.statusMessage = response.statusText

    // 回写响应头（跳过 hop-by-hop 头部）
    for (const [key, value] of response.headers.entries()) {
      if (['content-encoding', 'content-length'].includes(key)) {
        continue
      }
      if (key === 'set-cookie') {
        // 需要时处理 cookie 重写，这里直接透传
      }
      event.node.res.setHeader(key, value)
    }

    // 流式转发响应体（SSE 场景下连接保持打开）
    if (response.body) {
      return sendStream(event, response.body)
    }
  } catch (error) {
    /* 后端服务不可达时，返回 502 Bad Gateway */
    throw createError({
      statusCode: 502,
      statusMessage: 'Bad Gateway',
      message: '后端服务不可达，请确认后端服务已启动',
    })
  }
})
