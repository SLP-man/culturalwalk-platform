<script setup lang="ts">
withDefaults(
  defineProps<{
    lines?: number
    height?: string
  }>(),
  { lines: 3, height: '14px' },
)
</script>

<template>
  <div class="skeleton-box" aria-hidden="true">
    <div
      v-for="index in lines"
      :key="index"
      class="skeleton"
      :style="{ height, width: index === lines ? '62%' : '100%' }"
    />
  </div>
</template>

<style scoped>
.skeleton-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
