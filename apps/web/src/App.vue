<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { NAV_TABS } from '@/shared/nav'

// 全站壳：顶部标题 + 底部 5 个主 tab。
// 高亮哪个 tab 由路由的 meta.nav 决定，所以 /routes/:id、/authoring/:id 这类
// 子路径也会留在所属 tab 上，而不是把底部导航全灭掉。
const route = useRoute()
const activeKey = computed(() => route.meta.nav ?? null)
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

    <nav class="tabbar" aria-label="主导航">
      <RouterLink
        v-for="tab in NAV_TABS"
        :key="tab.key"
        :to="tab.to"
        class="tab"
        :class="{ active: activeKey === tab.key }"
        :aria-current="activeKey === tab.key ? 'page' : undefined"
      >
        {{ tab.label }}
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
  grid-template-columns: repeat(5, 1fr);
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
.tab.active {
  color: var(--brand);
  font-weight: 600;
}
</style>
