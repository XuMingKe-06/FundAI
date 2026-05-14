import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'

export default defineNuxtPlugin((nuxtApp) => {
  // 配置 Element Plus 中文语言
  nuxtApp.vueApp.provide('locale', zhCn)
  
  // 配置 ID 注入，解决 SSR 环境下的 IdInjection 警告
  nuxtApp.vueApp.provide(ID_INJECTION_KEY, {
    prefix: Math.floor(Math.random() * 10000),
    current: 0,
  })
  
  // 配置 z-index 注入，解决 SSR 环境下的 ZIndexInjection 警告
  nuxtApp.vueApp.provide(ZINDEX_INJECTION_KEY, {
    current: 2000,
  })
})
