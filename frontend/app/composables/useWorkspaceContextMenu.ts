/**
 * 工作台右键菜单组合式函数
 *
 * 封装右键菜单的显示/隐藏、会话删除确认等逻辑
 */

import { useSessionStore } from '~/stores/session'
import { useAnalysisStore } from '~/stores/analysis'
import { useAgentStore } from '~/stores/agent'
import type { Session } from '~/services/session.service'

export function useWorkspaceContextMenu() {
  const sessionStore = useSessionStore()
  const analysisStore = useAnalysisStore()
  const agentStore = useAgentStore()

  const contextMenuVisible = ref(false)
  const contextMenuX = ref(0)
  const contextMenuY = ref(0)
  const contextMenuTarget = ref<Session | null>(null)

  /* 显示右键菜单 */
  function handleRightClick(event: MouseEvent, chat: Session) {
    contextMenuTarget.value = chat
    contextMenuX.value = event.clientX
    contextMenuY.value = event.clientY
    contextMenuVisible.value = true
  }

  /* 关闭右键菜单 */
  function closeContextMenu() {
    contextMenuVisible.value = false
    contextMenuTarget.value = null
  }

  /* 确认删除会话 */
  async function confirmDeleteSession() {
    const target = contextMenuTarget.value
    if (!target) return

    closeContextMenu()

    try {
      await ElMessageBox.confirm(
        `确定要删除基金「${target.fundName}」(${target.fundCode})的分析会话吗？删除后不可恢复。`,
        '删除确认',
        { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning', confirmButtonClass: 'btn-delete-confirm' }
      )
    } catch {
      /* 用户取消删除 */
      return
    }

    /* 如果删除的是当前会话，清空报告 */
    if (sessionStore.currentSession?.id === target.id) {
      analysisStore.clearReport()
      agentStore.resetAgents()
    }

    const result = await sessionStore.deleteSession(target.id)
    if (result.success) {
      ElMessage.success('会话已删除')
    } else {
      ElMessage.error(result.error || '删除会话失败')
    }
  }

  /* 初始化全局点击处理器（关闭右键菜单） */
  function setupGlobalClickHandler() {
    if (import.meta.client) {
      document.addEventListener('click', () => {
        if (contextMenuVisible.value) {
          closeContextMenu()
        }
      })
      /* 监听滚动时关闭菜单 */
      document.addEventListener('scroll', closeContextMenu, true)
    }
  }

  /* 清理全局点击处理器 */
  function cleanupGlobalClickHandler() {
    if (import.meta.client) {
      document.removeEventListener('click', closeContextMenu)
      document.removeEventListener('scroll', closeContextMenu, true)
    }
  }

  return {
    contextMenuVisible,
    contextMenuX,
    contextMenuY,
    contextMenuTarget,
    handleRightClick,
    closeContextMenu,
    confirmDeleteSession,
    setupGlobalClickHandler,
    cleanupGlobalClickHandler,
  }
}
