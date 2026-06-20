<template>
  <aside class="sidebar-left" :class="{ collapsed: collapsed }">
    <template v-if="!collapsed">
      <!-- 搜索框 -->
      <div class="sidebar-search">
        <input
          :value="search"
          type="text"
          placeholder="搜索基金..."
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
        >
      </div>
      <!-- 会话列表 -->
      <div class="chat-list">
        <div v-if="loading" class="loading-indicator">
          加载中...
        </div>
        <div v-else-if="!hasSessions" class="empty-state">
          暂无历史会话
        </div>
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
    </template>
    <template v-else>
      <div class="collapsed-list">
        <div
          v-for="chat in filteredChatList.slice(0, 10)"
          :key="chat.id"
          class="collapsed-item"
          :class="{ active: currentSessionId === chat.id }"
          :title="`${chat.fundCode} ${chat.fundName}`"
          @click="$emit('selectSession', chat.id)"
        >
          <span class="collapsed-code">{{ chat.fundCode.slice(-4) }}</span>
        </div>
      </div>
    </template>
    <button class="btn-collapse" :title="collapsed ? '展开侧边栏' : '折叠侧边栏'" @click="$emit('toggleCollapse')">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline v-if="collapsed" points="9 18 15 12 9 6"/>
        <polyline v-else points="15 18 9 12 15 6"/>
      </svg>
    </button>
    <div
      v-if="contextMenuVisible"
      class="context-menu"
      :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
      @click.stop
    >
      <div class="context-menu-item danger" @click="$emit('deleteSession')">
        <span>删除会话</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { formatTime, getStatusText, getDecisionClass } from '~/utils/format'
import type { Session } from '~/services/session.service'

const props = defineProps<{
  search: string
  sessions: Session[]
  currentSessionId: string | undefined
  loading: boolean
  hasSessions: boolean
  contextMenuVisible: boolean
  contextMenuX: number
  contextMenuY: number
  collapsed: boolean
}>()

defineEmits<{
  'update:search': [value: string]
  'selectSession': [sessionId: string]
  'rightClick': [event: MouseEvent, chat: Session]
  'deleteSession': []
  'toggleCollapse': []
}>()

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
  padding: var(--space-5);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.collapsed-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.collapsed-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin: 0 auto var(--space-1);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.collapsed-item:hover {
  background: var(--bg-hover);
}

.collapsed-item.active {
  background: var(--bg-selected);
  color: var(--color-primary-500);
  font-weight: var(--font-semibold);
}

.btn-collapse {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 36px;
  border: none;
  border-top: 1px solid var(--border-base);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-collapse:hover {
  background: var(--bg-hover);
  color: var(--color-primary-500);
}

.context-menu {
  position: fixed;
  z-index: var(--z-popover);
  min-width: 140px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--space-1) 0;
  overflow: hidden;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
  user-select: none;
}

.context-menu-item:hover {
  background: var(--bg-hover);
}

.context-menu-item.danger {
  color: var(--color-danger-500);
}

.context-menu-item.danger:hover {
  background: var(--color-danger-50);
}

:deep(.btn-delete-confirm) {
  background-color: var(--color-danger-500) !important;
  border-color: var(--color-danger-500) !important;
}
</style>
