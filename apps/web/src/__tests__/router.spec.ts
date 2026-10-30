/**
 * 路由表测试：地址 → 页面 → 底部导航高亮的对应关系。
 *
 * nav.spec 测的是「渲染出来高亮对不对」，这里测路由表本身，
 * 改路由时能在第一时间发现自己把某个页面挂错了 tab、或把未知地址弄成白屏。
 */
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import { createAppRouter } from '@/router'

function router() {
  return createAppRouter(createMemoryHistory())
}

describe('路由表', () => {
  it('八条业务路由都指到已存在的组件，且名字唯一', () => {
    const r = router()
    const names = r.getRoutes().map((route) => route.name).filter(Boolean)

    expect(new Set(names).size).toBe(names.length)
    for (const path of ['/', '/routes/1', '/planner', '/authoring', '/submit', '/me', '/login', '/admin']) {
      expect(r.resolve(path).matched.length, path).toBeGreaterThan(0)
    }
  })

  it('详情页留在「发现」tab 上，编辑页留在「创作」tab 上', () => {
    const r = router()

    expect(r.resolve('/routes/r1').meta.nav).toBe('browse')
    expect(r.resolve('/authoring').meta.nav).toBe('authoring')
    expect(r.resolve('/authoring/draft-1').meta.nav).toBe('authoring')
  })

  it('登录页与审核后台不属于任何主 tab', () => {
    const r = router()

    expect(r.resolve('/login').meta.nav).toBeUndefined()
    expect(r.resolve('/admin').meta.nav).toBeUndefined()
  })

  it('未知地址回首页，不白屏', async () => {
    const r = router()
    await r.push('/this-page-does-not-exist')
    await r.isReady()

    expect(r.currentRoute.value.path).toBe('/')
  })
})
