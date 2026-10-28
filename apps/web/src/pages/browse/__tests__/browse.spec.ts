import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Schemas } from '@/api/types'
import RouteCard from '@/modules/route-card/index.vue'
import { EMPTY_FILTERS, buildRouteQuery, hasActiveFilter, rankThemes } from '../filters'

describe('buildRouteQuery', () => {
  it('只有 limit 时不下发空筛选参数', () => {
    expect(buildRouteQuery(EMPTY_FILTERS, null, 6)).toBe('limit=6')
  })

  it('按契约拼 q/theme/duration/channel 并去掉首尾空格', () => {
    const query = buildRouteQuery(
      { q: '  书店 ', theme: '亲子', duration: '120-240', channel: 'official' },
      null,
      6,
    )
    expect(query).toBe('q=%E4%B9%A6%E5%BA%97&theme=%E4%BA%B2%E5%AD%90&duration=120-240&channel=official&limit=6')
    const params = new URLSearchParams(query)
    expect(params.get('q')).toBe('书店')
    expect(params.get('theme')).toBe('亲子')
  })

  it('加载更多时带上 cursor', () => {
    expect(new URLSearchParams(buildRouteQuery(EMPTY_FILTERS, '6', 6)).get('cursor')).toBe('6')
  })
})

describe('hasActiveFilter', () => {
  it('纯空格的搜索词不算筛选', () => {
    expect(hasActiveFilter({ ...EMPTY_FILTERS, q: '   ' })).toBe(false)
  })

  it('任一条件有值就算筛选', () => {
    expect(hasActiveFilter({ ...EMPTY_FILTERS, duration: '0-120' })).toBe(true)
    expect(hasActiveFilter({ ...EMPTY_FILTERS, channel: 'user' })).toBe(true)
  })
})

describe('rankThemes', () => {
  it('按出现次数排序、去重、最多 10 个', () => {
    const pool = ['旧书店', '亲子', '旧书店', '旧书店', '夜游', '亲子']
    expect(rankThemes(pool, '')).toEqual(['旧书店', '亲子', '夜游'])

    const many = Array.from({ length: 14 }, (_, index) => 'tag' + index)
    expect(rankThemes(many, '')).toHaveLength(10)
  })

  it('已选中的主题即使不在池子里也保留在首位', () => {
    expect(rankThemes(['旧书店', '亲子'], '夜游')).toEqual(['夜游', '旧书店', '亲子'])
  })
})

describe('route-card', () => {
  async function renderCard(route: Schemas['RouteSummary']): Promise<string> {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }],
    })
    const app = createSSRApp({ render: () => h(RouteCard, { route }) })
    app.use(router)
    await router.push('/')
    await router.isReady()
    return renderToString(app)
  }

  it('展示标题/摘要/主题/时长/费用/互动数/作者/来源，并整卡链到详情页', async () => {
    const html = await renderCard({
      id: 'r1',
      title: '湘江边的旧书店',
      summary: '沿着湘江走三家旧书店',
      channel: 'user',
      author: { id: 'u1', username: '文化漫步者' },
      theme_tags: ['旧书店', '亲子'],
      duration_minutes: 150,
      cost: { min_total: 4500, max_total: 6000, currency: 'CNY' },
      comment_count: 3,
      favorite_count: 12,
    })

    expect(html).toContain('href="/routes/r1"')
    expect(html).toContain('湘江边的旧书店')
    expect(html).toContain('沿着湘江走三家旧书店')
    expect(html).toContain('旧书店')
    expect(html).toContain('亲子')
    expect(html).toContain('2 小时 30 分')
    expect(html).toContain('¥45-¥60')
    expect(html).toContain('3 评论')
    expect(html).toContain('12 收藏')
    expect(html).toContain('文化漫步者')
    expect(html).toContain('用户投稿')
  })
})
