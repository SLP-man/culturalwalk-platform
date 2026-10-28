import { describe, expect, it } from 'vitest'

import {
  buildNodePayload,
  costText,
  costUnknownHint,
  fenToYuan,
  isPriceInputValid,
  moveNode,
  normalizeTransport,
  removeNode,
  validateNodes,
  yuanToFen,
} from './draft'
import type { EditableNode } from './draft'

function node(overrides: Partial<EditableNode> = {}): EditableNode {
  return {
    uid: 'u-1',
    place_id: 'p-1',
    name: '第一师范',
    district: '天心区',
    stay_minutes: 60,
    transport: 'walk',
    note: '',
    price_yuan: '',
    ...overrides,
  }
}

describe('金额换算（接口分 / 输入元）', () => {
  it('元字符串换成分，写回时两位都等于这个分', () => {
    expect(yuanToFen('12.5')).toBe(1250)
    expect(yuanToFen('0')).toBe(0)
    expect(yuanToFen('  8 ')).toBe(800)
    expect(yuanToFen('')).toBeNull()
    expect(yuanToFen('-1')).toBeNull()
    expect(yuanToFen('abc')).toBeNull()
  })

  it('分回填到输入框，空值给空串让占位提示接管', () => {
    expect(fenToYuan(3200)).toBe('32')
    expect(fenToYuan(0)).toBe('0')
    expect(fenToYuan(2050)).toBe('20.5')
    expect(fenToYuan(null)).toBe('')
    expect(fenToYuan(undefined)).toBe('')
  })

  it('留空算合法（价格待核实），乱写不合法', () => {
    expect(isPriceInputValid('')).toBe(true)
    expect(isPriceInputValid('0')).toBe(true)
    expect(isPriceInputValid('1.5')).toBe(true)
    expect(isPriceInputValid('免费')).toBe(false)
  })
})

describe('节点排序与删除只在本地数组上做', () => {
  const list = ['a', 'b', 'c']

  it('上移下移换位置，不修改原数组', () => {
    expect(moveNode(list, 0, 1)).toEqual(['b', 'a', 'c'])
    expect(moveNode(list, 2, 1)).toEqual(['a', 'c', 'b'])
    expect(list).toEqual(['a', 'b', 'c'])
  })

  it('越界或原地不动时返回等值副本', () => {
    expect(moveNode(list, 0, -1)).toEqual(list)
    expect(moveNode(list, 2, 3)).toEqual(list)
    expect(moveNode(list, 1, 1)).toEqual(list)
    expect(moveNode(list, 0, -1)).not.toBe(list)
  })

  it('删除按位置移除，越界不动', () => {
    expect(removeNode(list, 1)).toEqual(['a', 'c'])
    expect(removeNode(list, 5)).toEqual(list)
  })
})

describe('保存前校验', () => {
  it('空节点表直接通过（可以存空草稿）', () => {
    expect(validateNodes([])).toBeNull()
  })

  it('停留分钟必须大于 0', () => {
    expect(validateNodes([node({ stay_minutes: 0 })])).toBe('第 1 个节点的停留分钟要大于 0')
    expect(validateNodes([node({ stay_minutes: Number.NaN })])).toBe(
      '第 1 个节点的停留分钟要大于 0',
    )
  })

  it('价格乱写给到具体节点序号', () => {
    expect(validateNodes([node(), node({ price_yuan: '面议' })])).toBe(
      '第 2 个节点的门票价格要填非负数字',
    )
  })

  it('合法节点不报错', () => {
    expect(validateNodes([node({ price_yuan: '20' })])).toBeNull()
  })
})

describe('PUT /route-drafts/{id}/nodes 载荷', () => {
  it('place_id 取 node.place 的 id，门票 price_min 与 price_max 相等', () => {
    const payload = buildNodePayload([
      node({ place_id: 'p-1', price_yuan: '20', note: '  斋饭 11:00 开  ' }),
      node({ place_id: 'p-2', price_yuan: '' }),
    ])
    expect(payload).toEqual([
      {
        place_id: 'p-1',
        stay_minutes: 60,
        transport: 'walk',
        note: '斋饭 11:00 开',
        price_min: 2000,
        price_max: 2000,
      },
      {
        place_id: 'p-2',
        stay_minutes: 60,
        transport: 'walk',
        note: null,
        price_min: null,
        price_max: null,
      },
    ])
  })

  it('交通值按枚举归一，脏值退回步行', () => {
    expect(normalizeTransport('metro')).toBe('metro')
    expect(normalizeTransport(undefined)).toBe('walk')
    expect(normalizeTransport('ufo')).toBe('walk')
  })
})

describe('预算展示', () => {
  it('用 moneyRange 展示接口返回的 cost', () => {
    expect(costText({ min_total: 200, max_total: 200, currency: 'CNY', unknown_count: 0 })).toBe(
      '¥2',
    )
    expect(costText({ min_total: 0, max_total: 200, currency: 'CNY', unknown_count: 0 })).toBe(
      '¥0-¥2',
    )
    expect(costText(null)).toBe('价格待核实')
  })

  it('unknown_count 大于 0 才提示缺价格', () => {
    expect(costUnknownHint({ min_total: 0, max_total: 0, currency: 'CNY', unknown_count: 3 })).toBe(
      '还有 3 个节点缺价格',
    )
    expect(costUnknownHint({ currency: 'CNY', unknown_count: 0 })).toBe('')
    expect(costUnknownHint(undefined)).toBe('')
  })
})
