<script setup lang="ts">
// 可复用业务组件：审核队列（任务列表与状态机按钮）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
defineProps<{}>()
</script>

<template>
  <div class="card">
    <p><strong>审核队列</strong></p>
    <p class="muted">任务列表与状态机按钮 —— 待实现</p>
  </div>
</template>
