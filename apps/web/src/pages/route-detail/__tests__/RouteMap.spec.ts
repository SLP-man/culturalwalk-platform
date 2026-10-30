import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it } from 'vitest'

import RouteMap from '../RouteMap.vue'

describe('RouteMap', () => {
  it('按序号画点位，并带上「不代表最短路径」的旁注', async () => {
    const html = await renderToString(
      createSSRApp(RouteMap, {
        pins: [
          { index: 1, name: '岳麓书院', x: 30, y: 40 },
          { index: 2, name: '爱晚亭', x: 70, y: 60 },
        ],
      }),
    )
    expect(html).toContain('仅展示点位，不代表最短路径或实时路况')
    expect(html).toContain('viewBox="0 0 100 100"')
    expect(html.match(/class="pin-dot"/g)).toHaveLength(2)
    expect([...html.matchAll(/class="pin-index"[^>]*>(\d)</g)].map((hit) => hit[1])).toEqual(['1', '2'])
  })
})
