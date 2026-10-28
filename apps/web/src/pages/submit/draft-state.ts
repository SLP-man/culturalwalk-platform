/**
 * FE-06 的纯逻辑：状态映射、退回理由挑选、成本文案。
 * 抽成纯函数是为了能直接用 vitest 测，不用起 DOM。
 */

import type { Schemas } from '@/api/types'
import { moneyRange } from '@/shared/format'

export type DraftState = Schemas['RouteDraft']['state']
export type Draft = Schemas['RouteDraft']
export type Notification = Schemas['Notification']

/** 不同状态给不同底色，光靠文案区分太弱。 */
const STATE_TONE: Record<DraftState, string> = {
  EDITING: 'state-editing',
  SUBMITTED_LOCKED: 'state-reviewing',
  APPROVED_LOCKED: 'state-approved',
  ARCHIVED: 'state-archived',
}

export function stateTone(state: DraftState): string {
  return STATE_TONE[state]
}

/** 只有 EDITING 的草稿能提交；锁定态只展示不可点。 */
export function canSubmit(state: DraftState): boolean {
  return state === 'EDITING'
}

export function submitButtonLabel(state: DraftState): string {
  switch (state) {
    case 'EDITING':
      return '提交审核'
    case 'SUBMITTED_LOCKED':
      return '审核中'
    case 'APPROVED_LOCKED':
      return '已通过'
    default:
      return '已归档'
  }
}

/** 提交成功后就地改状态，不必等列表回来才变「审核中」。 */
export function markSubmitted(items: readonly Draft[], id: string): Draft[] {
  return items.map((item) => (item.id === id ? { ...item, state: 'SUBMITTED_LOCKED' } : item))
}

/** 成本以「分」存，展示才换成元；缺价节点数单独说明，否则区间会骗人。 */
export function draftCostLabel(cost: Schemas['CostSummary'] | null | undefined): string {
  if (!cost) return '费用待核实'
  const range = moneyRange(cost.min_total, cost.max_total)
  const unknown = cost.unknown_count ?? 0
  return unknown > 0 ? `${range}（${unknown} 个节点待核价）` : range
}

export function nodeCountLabel(nodes: readonly unknown[] | null | undefined): string {
  const count = nodes ? nodes.length : 0
  return count > 0 ? `${count} 个节点` : '还没有节点'
}

/** 退回理由只认 review_request_changes，且取最新一条；reason 不是字符串就当没有。 */
export function latestReviewReason(items: readonly Notification[]): string | null {
  const hits = items
    .filter((item) => item.type === 'review_request_changes')
    .slice()
    .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
  const reason = hits[0]?.payload?.reason
  if (typeof reason !== 'string') return null
  const trimmed = reason.trim()
  return trimmed ? trimmed : null
}
