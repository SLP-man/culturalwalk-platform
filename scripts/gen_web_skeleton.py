# -*- coding: utf-8 -*-
"""生成 apps/web 的可运行前端骨架（Vue3 + TS + Vite + vue-router）。

页面全部是占位组件：能路由、能构建、有统一请求封装，但没有业务。
认领前端任务卡的人只改自己那个页面目录。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"

FILES: dict[str, str] = {}

FILES["package.json"] = """{
  "name": "culturalwalk-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port 5173",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --port 4173",
    "lint": "eslint src --ext .ts,.vue",
    "typecheck": "vue-tsc --noEmit",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "gen": "node ../packages/contracts/gen.mjs"
  },
  "dependencies": {
    "vue": "^3.5.12",
    "vue-router": "^4.4.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vue-tsc": "^2.1.10",
    "vitest": "^2.1.4"
  }
}
"""

FILES["vite.config.ts"] = """import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      // 前端只调 /api，代理到后端；不要在前端硬编码后端域名
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
"""

FILES["tsconfig.json"] = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "types": ["vite/client"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "env.d.ts"]
}
"""

FILES["env.d.ts"] = """/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
"""

FILES["index.html"] = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>CulturalWalk · 文化行走</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
"""

FILES["src/main.ts"] = """import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles/base.css'

createApp(App).use(router).mount('#app')
"""

FILES["src/App.vue"] = """<script setup lang="ts">
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
"""

FILES["src/styles/base.css"] = """:root {
  --brand: #8c3b2e;
  --ink: #1f1d1a;
  --muted: #77716a;
  --line: #e6e1da;
  --bg: #fbf8f4;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
}

a {
  color: inherit;
  text-decoration: none;
}

.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}

.muted {
  color: var(--muted);
  font-size: 13px;
}

.badge {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1ece5;
  color: var(--muted);
}

.btn {
  display: inline-block;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--brand);
  background: var(--brand);
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}

.btn.ghost {
  background: transparent;
  color: var(--brand);
}
"""

FILES["src/shared/api.ts"] = """/**
 * 统一请求封装。页面里不要直接 fetch。
 *
 * 约定（见 docs/03-接口契约规范.md）：
 * - 前缀 /api/v1，由 vite 代理到后端
 * - 写操作自动带 Idempotency-Key
 * - 非 2xx 抛 ApiError，页面按 code 分支而不是 message 文案
 */

export interface ApiErrorBody {
  error: { code: string; message: string; request_id?: string; details?: unknown[] }
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const BASE = '/api/v1'

function uuid(): string {
  return crypto.randomUUID()
}

let accessToken: string | null = localStorage.getItem('cw_token')
export function setToken(token: string | null): void {
  accessToken = token
  if (token) localStorage.setItem('cw_token', token)
  else localStorage.removeItem('cw_token')
}

export async function request<T>(
  path: string,
  init: RequestInit & { idempotent?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (init.idempotent ?? init.method && init.method !== 'GET') {
    headers.set('Idempotency-Key', uuid())
  }

  const res = await fetch(BASE + path, { ...init, headers })

  if (res.status === 204) return undefined as T

  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const err = data as ApiErrorBody | null
    throw new ApiError(
      res.status,
      err?.error.code ?? 'UNKNOWN',
      err?.error.message ?? `请求失败（${res.status}）`,
      err?.error.request_id,
    )
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown, lockVersion: number) =>
    request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
      headers: { 'If-Match': String(lockVersion) },
    }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
"""

FILES["src/router.ts"] = """import { createRouter, createWebHistory } from 'vue-router'

// 页面按目录一一对应 docs/00-总体开发文档.md §9 的 pages/ 列表
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'browse', component: () => import('@/pages/browse/index.vue') },
    {
      path: '/routes/:id',
      name: 'route-detail',
      component: () => import('@/pages/route-detail/index.vue'),
    },
    { path: '/planner', name: 'planner', component: () => import('@/pages/planner/index.vue') },
    { path: '/authoring', name: 'authoring', component: () => import('@/pages/authoring/index.vue') },
    { path: '/authoring/:id', name: 'authoring-edit', component: () => import('@/pages/authoring/index.vue') },
    { path: '/submit', name: 'submit', component: () => import('@/pages/submit/index.vue') },
    { path: '/me', name: 'me', component: () => import('@/pages/me/index.vue') },
    { path: '/login', name: 'login', component: () => import('@/pages/login/index.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/pages/admin/index.vue') },
  ],
})
"""

PAGE_TEMPLATE = """<script setup lang="ts">
// {desc}
// 任务卡：{card}
// TODO: 数据请求统一走 @/shared/api，不要在组件里 fetch
</script>

<template>
  <div>
    <h2>{title}</h2>
    <p class="muted">{desc}</p>

    <div class="card">
      <p><strong>本页待实现</strong></p>
      <ul>
{bullets}
      </ul>
    </div>
  </div>
</template>
"""

PAGES = {
    "browse": ("发现", "路线列表与筛选", "FE-02", ["路线卡片列表（封面/标题/主题/时长/费用区间）", "主题与时长筛选条", "关键词搜索输入", "加载骨架屏 / 空结果提示"]),
    "route-detail": ("路线详情", "节点时间线、来源、地图点位", "FE-03", ["每日节点时间线（顺序/停留/交通）", "每点位的文化说明与来源折叠", "费用区间与「待核实」标记", "地图点位 + 外部导航跳转", "评论列表与收藏按钮"]),
    "planner": ("规划行程", "输入条件 → 生成 → 转草稿", "FE-07", ["城市/天数/人数/预算/偏好表单", "缺字段时的追问提示", "生成进度（四步 Agent 各自状态）", "结果：日程、费用区间、来源", "保存 / 分享链接 / 转成路线草稿"]),
    "authoring": ("创作路线", "草稿编辑", "FE-05", ["新建草稿表单", "添加节点（从地点库选）", "拖拽排序与停留时长", "每节点填来源与图片", "保存草稿（带 If-Match 并发保护）"]),
    "submit": ("我的路线", "草稿状态与提交审核", "FE-06", ["我的草稿列表与状态标签", "提交审核（确认弹窗）", "撤回投稿", "退回理由展示与再编辑入口"]),
    "me": ("我的主页", "用户名、简介、已发布路线", "FE-09", ["个人资料展示", "我发布的路线列表", "我收藏的路线", "未读通知入口"]),
    "login": ("登录 / 注册", "账号入口", "FE-04", ["登录表单", "注册表单", "错误提示（按 error.code 区分）", "登录后回跳原页面"]),
    "admin": ("审核后台", "审核队列与发布", "FE-08", ["待审任务列表（OPEN / CLAIMED）", "领取 / 释放任务", "版本 diff 视图（节点增删改高亮）", "通过 / 退回（必填理由）", "发布与下线（下线须填原因）"]),
}

MODULES = {
    "route-card": ("路线卡片", "列表页与主页共用"),
    "planner-form": ("规划表单", "受控表单 + 校验，输出 PlanInput"),
    "review-queue": ("审核队列", "任务列表与状态机按钮"),
    "comment-thread": ("评论串", "列表 + 发表 + 作者置顶"),
}


def main() -> None:
    for rel, content in FILES.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    for name, (title, desc, card, bullets) in PAGES.items():
        path = ROOT / "src" / "pages" / name / "index.vue"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            PAGE_TEMPLATE.format(
                title=title,
                desc=desc,
                card=card,
                bullets="\n".join(f"        <li>{b}</li>" for b in bullets),
            ),
            encoding="utf-8",
        )

    for name, (title, desc) in MODULES.items():
        path = ROOT / "src" / "modules" / name / "index.vue"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""<script setup lang="ts">
// 可复用业务组件：{title}（{desc}）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
defineProps<{{}}>()
</script>

<template>
  <div class="card">
    <p><strong>{title}</strong></p>
    <p class="muted">{desc} —— 待实现</p>
  </div>
</template>
""",
            encoding="utf-8",
        )

    print(f"前端骨架完成：{len(FILES)} 个根文件，{len(PAGES)} 个页面，{len(MODULES)} 个组件")


if __name__ == "__main__":
    main()
