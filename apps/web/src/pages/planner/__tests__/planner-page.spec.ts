/**
 * 规划页（FE-07）冒烟测试。
 *
 * 表单本身的条件校验与换算在 modules/planner-form/plan-form.spec.ts 里测；
 * 这里只锁「页面能渲染、未登录不放行」。
 */
import { beforeAll, describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import type { Component } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'

const Blank: Component = { render: () => null }

let PlannerPage: Component

beforeAll(async () => {
  PlannerPage = (await import('../index.vue')).default
})

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/login', '/authoring', '/routes/:id'].map((path) => ({
      path,
      component: Blank,
    })),
  })
}

describe('/planner 未登录', () => {
  it('渲染规划页骨架，并提示需要登录', async () => {
    const app = createSSRApp(PlannerPage)
    app.use(router())
    const html = await renderToString(app)

    expect(html).toContain('规划行程')
    expect(html).toContain('登录后才能生成行程')
    expect(html).toContain('href="/login"')
  })
})
