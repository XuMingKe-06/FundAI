<template>
  <div class="app-container">
    <!-- 页面加载进度条 - 固定在页面最顶部 -->
    <NuxtLoadingIndicator
      color="#409EFF"
      :height="3"
      :duration="2000"
      :throttle="200"
    />
    <NuxtPage />
  </div>
</template>

<style>
/* 确保进度条在最顶层 */
.app-container {
  width: 100%;
  height: 100%;
}
</style>
