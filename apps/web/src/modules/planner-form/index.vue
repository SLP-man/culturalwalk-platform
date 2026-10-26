<script setup lang="ts">
// 可复用业务组件：规划表单（受控表单 + 校验，输出 PlanInput）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
defineProps<{}>()
</script>

<template>
  <div class="card">
    <p><strong>规划表单</strong></p>
    <p class="muted">受控表单 + 校验，输出 PlanInput —— 待实现</p>
  </div>
</template>
