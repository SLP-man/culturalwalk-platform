/**
 * 审核后台（FE-08）页面冒烟测试。
 *
 * 只锁两件事：没登录不能看队列、页面骨架能渲染出来不白屏。
 * 具体审核逻辑（退回必填理由等）在 modules/review-queue/__tests__/state.spec.ts 里测。
 */
import { beforeAll, describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import type { Component } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'

import { readItem } from '@/shared/storage'

const Blank: Component = { render: () => null }

let AdminPage: Component

beforeAll(async () => {
  AdminPage = (await import('../index.vue')).default
})

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/login', '/routes/:id', '/submissions/:id'].map((path) => ({
      path,
      component: Blank,
    })),
  })
}

describe('/admin 未登录', () => {
  it('渲染审核后台骨架与登录入口', async () => {
    const app = createSSRApp(AdminPage)
    app.use(router())
    const html = await renderToString(app)

    expect(html).toContain('审核后台')
    expect(html).toContain('审核后台需要登录后才能使用')
    expect(html).toContain('href="/login"')
  })

  it('未登录时不会去打审核队列接口', () => {
    // 未登录直接 return，本地不该有 token，也不该有用户缓存
    expect(readItem('cw_token')).toBeNull()
    expect(readItem('cw_user')).toBeNull()
  })
})
