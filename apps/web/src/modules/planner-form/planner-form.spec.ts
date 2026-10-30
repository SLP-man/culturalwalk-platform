import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it } from 'vitest'

import PlannerForm from './index.vue'
import { defaultForm } from './plan-form'

async function render(): Promise<string> {
  return renderToString(createSSRApp(PlannerForm, { modelValue: defaultForm() }))
}

describe('PlannerForm', () => {
  it('渲染全部选项，时段默认全选并在提交按钮上收口', async () => {
    const html = await render()

    for (const dayPart of ['上午', '下午', '晚上']) expect(html).toContain(dayPart)
    for (const theme of ['历史', '书院', '街巷', '市井', '博物馆', '江景', '亲子', '夜景']) {
      expect(html).toContain(theme)
    }
    for (const transport of ['步行', '地铁', '公交', '打车', '骑行']) expect(html).toContain(transport)
    for (const pace of ['轻松', '适中', '紧凑']) expect(html).toContain(pace)

    expect(html).toContain('开始规划')
    // 城市默认长沙；三个时段 + 步行/地铁两个交通 chip 默认选中
    expect(html).toContain('长沙')
    expect(html.match(/aria-pressed="true"/g)).toHaveLength(5)
  })
})
