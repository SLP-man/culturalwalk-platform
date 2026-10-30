/**
 * 草稿编辑的纯逻辑。放在组件外面是为了能直接跑单测，也避免模板里塞业务判断。
 * 金额单位约定：接口用「分」，输入框用「元」，这里负责两边换算。
 */

import type { Schemas } from '@/api/types'

import { moneyRange } from '@/shared/format'

/** 交通方式，与契约 RouteNodeInput.transport 的枚举一致 */
export type Transport = NonNullable<Schemas['RouteNodeInput']['transport']>

export const TRANSPORT_OPTIONS: Transport[] = ['walk', 'metro', 'bus', 'taxi', 'bike']

/** 编辑器里的节点：接口数据 + 表单输入需要的元字符串和 uid */
export type EditableNode = {
  uid: string
  place_id: string
  name: string
  district: string | null
  stay_minutes: number
  transport: Transport
  note: string
  price_yuan: string
}

export type DraftCost = Schemas['CostSummary']

export function normalizeTransport(value: string | null | undefined): Transport {
  const hit = TRANSPORT_OPTIONS.find((option) => option === value)
  return hit ?? 'walk'
}

/** 分 → 输入框里的元字符串；空值给空串，让占位提示接管 */
export function fenToYuan(fen: number | null | undefined): string {
  if (fen == null) return ''
  const yuan = fen / 100
  return Number.isInteger(yuan) ? String(yuan) : yuan.toFixed(2).replace(/0$/, '')
}

/** 元字符串 → 分；留空或非法返回 null（保存前由 validateNodes 拦非法输入） */
export function yuanToFen(text: string): number | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const yuan = Number(trimmed)
  if (!Number.isFinite(yuan) || yuan < 0) return null
  return Math.round(yuan * 100)
}

export function isPriceInputValid(text: string): boolean {
  const trimmed = text.trim()
  if (!trimmed) return true
  const yuan = Number(trimmed)
  return Number.isFinite(yuan) && yuan >= 0
}

/** 上移/下移。越界或原地不动时返回副本，页面不用自己判边界 */
export function moveNode<T>(list: readonly T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0 || from >= list.length || to >= list.length) {
    return list.slice()
  }
  const next = list.slice()
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

export function removeNode<T>(list: readonly T[], index: number): T[] {
  if (index < 0 || index >= list.length) return list.slice()
  return list.filter((_, itemIndex) => itemIndex !== index)
}

/** 返回第一条错误文案，全通过给 null；先本地拦，避免把无效数据发给接口 */
export function validateNodes(nodes: readonly EditableNode[]): string | null {
  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index]
    if (!node.place_id) return '第 ' + (index + 1) + ' 个节点没有绑定地点'
    const stay = Number(node.stay_minutes)
    if (!Number.isFinite(stay) || stay <= 0) return '第 ' + (index + 1) + ' 个节点的停留分钟要大于 0'
    if (!isPriceInputValid(node.price_yuan)) {
      return '第 ' + (index + 1) + ' 个节点的门票价格要填非负数字'
    }
  }
  return null
}

/** 门票只填一个价：写回时 price_min = price_max = 元 × 100 */
export function buildNodePayload(nodes: readonly EditableNode[]): Schemas['RouteNodeInput'][] {
  return nodes.map((node) => {
    const fen = yuanToFen(node.price_yuan)
    const note = node.note.trim()
    return {
      place_id: node.place_id,
      stay_minutes: Math.round(Number(node.stay_minutes)),
      transport: node.transport,
      note: note ? note : null,
      price_min: fen,
      price_max: fen,
    }
  })
}

export function costText(cost: DraftCost | null | undefined): string {
  if (!cost) return '价格待核实'
  return moneyRange(cost.min_total, cost.max_total)
}

export function costUnknownHint(cost: DraftCost | null | undefined): string {
  const count = cost?.unknown_count ?? 0
  return count > 0 ? '还有 ' + count + ' 个节点缺价格' : ''
}
