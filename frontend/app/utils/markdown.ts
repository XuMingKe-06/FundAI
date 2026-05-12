/**
 * Markdown 渲染工具
 *
 * 封装 MarkdownIt 渲染器，提供 LRU 缓存和 JSON 内容提取功能
 * 用于智能体思考过程和分析结果的 Markdown 渲染
 */

import MarkdownIt from 'markdown-it'

/* 初始化 Markdown 渲染器 */
const md = new MarkdownIt({
  html: false,
  breaks: false,
  linkify: true,
  typographer: true
})

/* Markdown 渲染缓存（LRU，最多缓存200条避免内存泄漏） */
const markdownCache = new Map<string, string>()
const MARKDOWN_CACHE_MAX = 200

/* 写入缓存的辅助函数 */
function putCache(key: string, value: string): void {
  if (markdownCache.size >= MARKDOWN_CACHE_MAX) {
    const firstKey = markdownCache.keys().next().value
    if (firstKey !== undefined) markdownCache.delete(firstKey)
  }
  markdownCache.set(key, value)
}

/**
 * 过滤并渲染 Markdown 内容
 *
 * LLM 输出通常为 ```json { "score":..., "summary": "markdown...", "details":{...} } ``` 格式，
 * 此函数尝试从 JSON 中提取 summary 字段作为显示内容，同时保留普通 markdown 文本的正常渲染。
 */
export function renderMarkdown(text: string): string {
  if (!text) return ''

  /* LRU 缓存：相同文本避免重复正则+JSON+渲染开销 */
  const cached = markdownCache.get(text)
  if (cached !== undefined) return cached

  let processedText = text

  /* ---- 步骤1：尝试从 JSON 格式中提取 summary 字段 ---- */
  const trimmedText = text.trim()
  let jsonStr = ''
  /* 情况A：文本整体是一个裸 JSON 对象 */
  if (trimmedText.startsWith('{') && trimmedText.endsWith('}')) {
    jsonStr = trimmedText
  } else {
    /* 情况B：文本中包含 ```json 代码块，提取其中的 JSON 内容 */
    const jsonBlockMatch = text.match(/```json\s*([\s\S]*?)```/)
    if (jsonBlockMatch && jsonBlockMatch[1]) {
      const extracted = jsonBlockMatch[1].trim()
      if (extracted.startsWith('{') && extracted.endsWith('}')) {
        jsonStr = extracted
      }
    }
  }

  if (jsonStr) {
    try {
      const parsed = JSON.parse(jsonStr)
      if (parsed.summary && typeof parsed.summary === 'string') {
        /* 使用 summary 字段（markdown 格式文本） */
        processedText = parsed.summary
      } else if (parsed.details && typeof parsed.details === 'object') {
        /* 没有 summary 时，用 details 结构兜底 */
        const detailStr = JSON.stringify(parsed.details, null, 2)
        if (detailStr !== '{}') processedText = detailStr
      }
    } catch {
      /* JSON 解析失败，继续使用原文本 */
    }
  }

  /* ---- 步骤2：过滤残留的 JSON 代码块 ---- */
  processedText = processedText.replace(/```json[\s\S]*?```/g, '\n')

  /* ---- 步骤3：合并连续换行（更激进） ---- */
  processedText = processedText
    .replace(/\r\n/g, '\n')        /* 统一 Windows 换行符 */
    .replace(/\r/g, '\n')          /* 统一旧 Mac 换行符 */
    .replace(/\n\s*\n\s*\n/g, '\n\n')  /* 含空白字符的3个空行合并为段落分隔 */
    .replace(/\n{3,}/g, '\n\n')    /* 剩余3个以上换行合并 */
    .replace(/^[\s\n]+|[\s\n]+$/g, '')  /* 去掉首尾空白和空行 */

  /* ---- 步骤4：回退机制 ---- */
  if (!processedText) {
    /* 如果过滤后为空，显示原文前 200 字符，避免完全空白 */
    const fallback = text.trim().substring(0, 200)
    if (fallback) {
      const result = md.render(fallback)
      putCache(text, result)
      return result
    }
    return ''
  }

  const result = md.render(processedText)
  putCache(text, result)
  return result
}
