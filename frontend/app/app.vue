<template>
  <div class="app-container">
    <NuxtLoadingIndicator
      color="#409EFF"
      :height="3"
      :duration="2000"
      :throttle="200"
    />
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import { useTheme } from '~/composables/useTheme'

const { initTheme } = useTheme()

onMounted(() => {
  initTheme()
})
</script>

<style>
.app-container {
  width: 100%;
  height: 100%;
}
</style>
