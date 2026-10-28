/**
 * /me 页面冒烟：未登录时直接给登录入口。
 * session/api 在模块作用域读 localStorage，所以先打桩再动态 import。
 */
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { createSSRApp } from 'vue'
import type { Component } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'

const store = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => void store.set(key, value),
  removeItem: (key: string) => void store.delete(key),
})

const Blank: Component = { render: () => null }

let MePage: Component

beforeAll(async () => {
  MePage = (await import('./index.vue')).default
})

describe('/me 未登录', () => {
  it('渲染登录引导并指向 /login', async () => {
    const app = createSSRApp(MePage)
    app.use(
      createRouter({
        history: createMemoryHistory(),
        routes: ['/', '/login', '/authoring', '/admin', '/routes/:id'].map((path) => ({
          path,
          component: Blank,
        })),
      }),
    )
    const html = await renderToString(app)
    expect(html).toContain('我的主页')
    expect(html).toContain('登录后查看我的主页')
    expect(html).toContain('href="/login"')
  })
})
