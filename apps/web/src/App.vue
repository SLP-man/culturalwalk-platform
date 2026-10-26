<script setup lang="ts">
// 全站壳：顶部标题 + 底部导航。登录态等全局状态后续放 shared/store.ts
const tabs = [
  { to: '/', label: '发现' },
  { to: '/planner', label: '规划' },
  { to: '/authoring', label: '创作' },
  { to: '/me', label: '我的' },
]
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <strong>文化行走</strong>
      <span class="hint">长沙 · 原型</span>
    </header>

    <main class="page">
      <RouterView />
    </main>

    <nav class="tabbar">
      <RouterLink v-for="t in tabs" :key="t.to" :to="t.to" class="tab">
        {{ t.label }}
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
}
.hint {
  font-size: 12px;
  color: var(--muted);
}
.page {
  flex: 1;
  padding: 16px;
  padding-bottom: 72px;
}
.tabbar {
  position: fixed;
  inset: auto 0 0 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--line);
  background: #fff;
  padding-bottom: env(safe-area-inset-bottom);
}
.tab {
  text-align: center;
  padding: 12px 0;
  font-size: 14px;
  color: var(--muted);
}
.tab.router-link-active {
  color: var(--brand);
  font-weight: 600;
}
</style>
