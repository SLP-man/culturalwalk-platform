<script setup lang="ts">
// 可复用业务组件：路线卡片（列表页与主页共用）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
defineProps<{}>()
</script>

<template>
  <div class="card">
    <p><strong>路线卡片</strong></p>
    <p class="muted">列表页与主页共用 —— 待实现</p>
  </div>
</template>
