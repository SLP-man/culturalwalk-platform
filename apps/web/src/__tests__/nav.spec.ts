/**
 * FE-01 验收测试：5 个主 tab 可切换。
 *
 * 用 SSR 渲染真实的 App + router（内存 history），不引入 jsdom 之类的新依赖：
 * 每个 tab 渲染一次，断言「只有它高亮」且「页面内容确实换成了对应页」。
 */

import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory } from 'vue-router'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { NAV_TABS } from '@/shared/nav'

/** 每个 tab 落地页里独有的文案，用来证明页面真的换了 */
const PAGE_MARKERS = ['发现', '规划行程', '创作路线', '我的路线', '我的主页']

async function renderAt(path: string): Promise<string> {
  const router = createAppRouter(createMemoryHistory())
  const app = createSSRApp(App)
  app.use(router)
  await router.push(path)
  await router.isReady()
  return renderToString(app)
}

function activeTabCount(html: string): number {
  return html.match(/aria-current="page"/g)?.length ?? 0
}

/** 取被标记成 aria-current="page" 的那个 tab 的 href（= 当前高亮的 tab） */
function activeTabHref(html: string): string | undefined {
  return html.match(/<a [^>]*aria-current="page"[^>]*href="([^"]+)"/)?.[1]
}

describe('底部导航（FE-01）', () => {
  it('恰好 5 个主 tab，且各自指向已注册的路由', () => {
    const router = createAppRouter(createMemoryHistory())

    expect(NAV_TABS).toHaveLength(5)
    expect(new Set(NAV_TABS.map((tab) => tab.key)).size).toBe(5)
    expect(new Set(NAV_TABS.map((tab) => tab.to)).size).toBe(5)

    for (const tab of NAV_TABS) {
      const resolved = router.resolve(tab.to)
      expect(resolved.name, `${tab.to} 应该能解析到具名路由`).toBeTruthy()
      expect(resolved.matched).toHaveLength(1)
      expect(resolved.meta.nav, `${tab.to} 的 meta.nav 应该指向自己`).toBe(tab.key)
    }
  })

  it.each(NAV_TABS.map((tab, index) => [tab.label, tab.to, index] as const))(
    '切到「%s」(%s) 时只有它高亮，页面内容也换成该页',
    async (label, to, index) => {
      const html = await renderAt(to)

      // 5 个 tab 始终都在
      for (const tab of NAV_TABS) {
        expect(html).toContain(tab.label)
        expect(html).toContain(`href="${tab.to}"`)
      }
      // 有且只有当前 tab 高亮，而且高亮的就是这一条
      expect(activeTabCount(html)).toBe(1)
      expect(activeTabHref(html)).toBe(to)
      // 落地页内容确实是这一页
      expect(html).toContain(PAGE_MARKERS[index])
    },
  )

  it('子路径留在父 tab 上：/routes/1 仍点亮「发现」，/authoring/1 仍点亮「创作」', async () => {
    for (const [path, nav] of [
      ['/routes/1', 'browse'],
      ['/authoring/1', 'authoring'],
    ] as const) {
      const router = createAppRouter(createMemoryHistory())
      await router.push(path)
      expect(router.currentRoute.value.meta.nav).toBe(nav)
    }
  })

  it('登录页与后台不点亮任何主 tab', async () => {
    for (const path of ['/login', '/admin']) {
      const html = await renderAt(path)
      expect(activeTabCount(html), `${path} 不该高亮主 tab`).toBe(0)
      expect(activeTabHref(html)).toBeUndefined()
    }
  })

  it('未知地址回首页，不白屏', async () => {
    const router = createAppRouter(createMemoryHistory())
    await router.push('/no-such-page')
    expect(router.currentRoute.value.name).toBe('browse')
    expect(router.currentRoute.value.path).toBe('/')

    const html = await renderAt('/no-such-page')
    expect(html).toContain('发现')
    expect(activeTabCount(html)).toBe(1)
  })
})
