<template>
  <aside class="sidebar-left">
    <div class="sidebar-search">
      <input
        :value="search"
        type="text"
        placeholder="搜索基金..."
        @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
      >
    </div>
    <div class="chat-list">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-indicator">
        加载中...
      </div>
      <!-- 空状态 -->
      <div v-else-if="!hasSessions" class="empty-state">
        暂无历史会话
      </div>
      <!-- 会话列表 -->
      <div
        v-for="chat in filteredChatList"
        :key="chat.id"
        class="chat-item"
        :class="{ active: currentSessionId === chat.id }"
        @click="$emit('selectSession', chat.id)"
        @contextmenu.prevent="$emit('rightClick', $event, chat)"
      >
        <div class="chat-fund">
          <span class="fund-code">{{ chat.fundCode }}</span>
          <span class="fund-name">{{ chat.fundName }}</span>
        </div>
        <div class="chat-meta">
          <span class="chat-time">{{ formatTime(chat.updatedAt) }}</span>
          <span class="chat-decision" :class="getDecisionClass(chat)">{{ getStatusText(chat) }}</span>
        </div>
      </div>
    </div>
    <!-- 右键菜单 -->
    <div
      v-if="contextMenuVisible"
      class="context-menu"
      :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
      @click.stop
    >
      <div class="context-menu-item danger" @click="$emit('deleteSession')">
        <span class="context-menu-icon">🗑</span>
        <span>删除会话</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
/* 工作台左侧会话列表组件 */

import { formatTime, getStatusText, getDecisionClass } from '~/utils/format'
import type { Session } from '~/services/session.service'

const props = defineProps<{
  /* 搜索关键词 */
  search: string
  /* 会话列表 */
  sessions: Session[]
  /* 当前选中的会话ID */
  currentSessionId: string | undefined
  /* 是否加载中 */
  loading: boolean
  /* 是否有会话 */
  hasSessions: boolean
  /* 右键菜单是否可见 */
  contextMenuVisible: boolean
  /* 右键菜单X坐标 */
  contextMenuX: number
  /* 右键菜单Y坐标 */
  contextMenuY: number
}>()

defineEmits<{
  /* 搜索关键词更新 */
  'update:search': [value: string]
  /* 选择会话 */
  'selectSession': [sessionId: string]
  /* 右键点击会话 */
  'rightClick': [event: MouseEvent, chat: Session]
  /* 删除会话 */
  'deleteSession': []
}>()

/* 过滤后的会话列表 */
const filteredChatList = computed(() => {
  const sessions = props.sessions
  if (!props.search.trim()) return sessions
  const keyword = props.search.trim().toLowerCase()
  return sessions.filter(session =>
    session.fundCode.toLowerCase().includes(keyword) ||
    session.fundName.toLowerCase().includes(keyword)
  )
})
</script>

<style scoped>
.loading-indicator,
.empty-state {
  padding: 20px;
  text-align: center;
  color: #909399;
}

.context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 140px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  overflow: hidden;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
  color: #303133;
  cursor: pointer;
  transition: background 0.15s;
  user-select: none;
}

.context-menu-item:hover {
  background: #f5f7fa;
}

.context-menu-item.danger {
  color: #F56C6C;
}

.context-menu-item.danger:hover {
  background: #fef0f0;
}

.context-menu-icon {
  font-size: 14px;
  line-height: 1;
}

:deep(.btn-delete-confirm) {
  background-color: #F56C6C !important;
  border-color: #F56C6C !important;
}

:deep(.btn-delete-confirm:hover) {
  background-color: #f78989 !important;
  border-color: #f78989 !important;
}
</style>
