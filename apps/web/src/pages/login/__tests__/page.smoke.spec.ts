import { describe, expect, it, vi } from 'vitest'

// 页面在 import 阶段会碰 localStorage（shared/api 读 token），node 环境先补一个
const memory = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
  removeItem: (key: string) => void memory.delete(key),
})

describe('login page smoke', () => {
  it('SSR 能渲染出登录表单与演示账号', async () => {
    const { createSSRApp } = await import('vue')
    const { renderToString } = await import('vue/server-renderer')
    const { createRouter, createMemoryHistory } = await import('vue-router')
    const Page = (await import('../index.vue')).default

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', component: Page },
        { path: '/', component: { template: '<div />' } },
      ],
    })
    await router.push('/login')
    await router.isReady()

    const html = await renderToString(createSSRApp(Page).use(router))
    expect(html).toContain('用户名')
    expect(html).toContain('密码')
    expect(html).toContain('演示账号')
    expect(html).toContain('文化漫步者')
    expect(html).toContain('审核编辑')
    expect(html).toContain('登录')
  })
})
