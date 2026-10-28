<script setup lang="ts">
defineProps<{
  title: string
  hint?: string
}>()
</script>

<template>
  <div class="empty">
    <p class="empty-title">{{ title }}</p>
    <p v-if="hint" class="muted">{{ hint }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: 28px 16px;
  text-align: center;
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: #fff;
}

.empty-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}
</style>
