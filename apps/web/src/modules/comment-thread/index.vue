<script setup lang="ts">
// 可复用业务组件：评论串（列表 + 发表 + 作者置顶）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
defineProps<{}>()
</script>

<template>
  <div class="card">
    <p><strong>评论串</strong></p>
    <p class="muted">列表 + 发表 + 作者置顶 —— 待实现</p>
  </div>
</template>
