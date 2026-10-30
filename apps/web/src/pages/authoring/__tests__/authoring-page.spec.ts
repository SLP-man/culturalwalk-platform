/**
 * 创作页（FE-05）冒烟测试。
 *
 * 草稿的纯逻辑在 pages/authoring/draft.spec.ts 里测；这里锁页面骨架与未登录引导。
 */
import { beforeAll, describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import type { Component } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'

const Blank: Component = { render: () => null }

let AuthoringPage: Component

beforeAll(async () => {
  AuthoringPage = (await import('../index.vue')).default
})

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/login', '/authoring', '/authoring/:id', '/submit'].map((path) => ({
      path,
      component: Blank,
    })),
  })
}

describe('/authoring 未登录', () => {
  it('渲染创作页骨架并引导登录', async () => {
    const app = createSSRApp(AuthoringPage)
    app.use(router())
    const html = await renderToString(app)

    expect(html).toContain('创作路线')
    expect(html).toContain('href="/login"')
  })
})
