import { createPinia } from 'pinia'

/* 创建 Pinia 实例 */
const pinia = createPinia()

/* 导出 Pinia 实例 */
export default pinia

/* 导出所有 store */
export * from './auth'
export * from './session'
export * from './analysis'
export * from './agent'
