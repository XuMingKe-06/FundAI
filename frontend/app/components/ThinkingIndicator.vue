<template>
  <Transition name="thinking-fade">
    <div v-if="visible" class="thinking-indicator">
      <span class="thinking-text">
        <span
          v-for="(char, index) in chars"
          :key="index"
          class="char"
          :class="{ visible: index < visibleCount }"
        >{{ char }}</span>
      </span>
    </div>
  </Transition>
</template>

<script setup lang="ts">
/* Thinking... 逐字符显示指示器组件 */

/* Props */
const props = defineProps<{
  visible: boolean
}>()

/* 要显示的文本 */
const text = 'Thinking...'
const chars = text.split('')

/* 当前可见的字符数量 */
const visibleCount = ref(0)

/* 动画定时器 */
let animationTimer: ReturnType<typeof setInterval> | null = null

/* 字符显示间隔（毫秒） */
const CHAR_INTERVAL = 150

/* 完整显示后的暂停时间（毫秒） */
const PAUSE_DURATION = 800

/* 开始动画 */
function startAnimation() {
  /* 清除之前的定时器 */
  if (animationTimer) {
    clearInterval(animationTimer)
  }
  
  visibleCount.value = 0
  
  /* 逐字符显示 */
  animationTimer = setInterval(() => {
    visibleCount.value++
    
    /* 所有字符显示完毕后，暂停一段时间再重新开始 */
    if (visibleCount.value >= chars.length) {
      clearInterval(animationTimer!)
      animationTimer = null
      
      /* 暂停后重新开始动画 */
      setTimeout(() => {
        if (props.visible) {
          startAnimation()
        }
      }, PAUSE_DURATION)
    }
  }, CHAR_INTERVAL)
}

/* 停止动画 */
function stopAnimation() {
  if (animationTimer) {
    clearInterval(animationTimer)
    animationTimer = null
  }
  visibleCount.value = 0
}

/* 监听 visible 变化 */
watch(() => props.visible, (newVal) => {
  if (newVal) {
    startAnimation()
  } else {
    stopAnimation()
  }
}, { immediate: true })

/* 组件卸载时清理 */
onUnmounted(() => {
  stopAnimation()
})
</script>

<style scoped>
.thinking-indicator {
  display: flex;
  align-items: center;
  padding: 0;
  background: transparent;
}

.thinking-text {
  display: flex;
  font-size: 14px;
  font-weight: 500;
  font-style: italic;
  color: #909399;
  letter-spacing: 1px;
}

.char {
  opacity: 0;
  transition: opacity 0.1s ease;
}

.char.visible {
  opacity: 1;
}

/* 淡入淡出过渡动画 */
.thinking-fade-enter-active,
.thinking-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.thinking-fade-enter-from,
.thinking-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
