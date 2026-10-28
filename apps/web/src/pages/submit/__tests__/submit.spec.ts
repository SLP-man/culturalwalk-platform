import { describe, expect, it } from 'vitest'

import type { Schemas } from '@/api/types'

import {
  canSubmit,
  draftCostLabel,
  latestReviewReason,
  markSubmitted,
  nodeCountLabel,
  stateTone,
  submitButtonLabel,
  type Draft,
} from '../draft-state'

function draft(id: string, state: Draft['state']): Draft {
  return {
    id,
    title: '草稿 ' + id,
    state,
    lock_version: 1,
    updated_at: '2026-06-01T09:20:00Z',
  }
}

describe('FE-06 提交审核卡片', () => {
  it('只有 EDITING 能提交，锁定状态按钮文案跟着状态走', () => {
    expect(canSubmit('EDITING')).toBe(true)
    expect(canSubmit('SUBMITTED_LOCKED')).toBe(false)
    expect(canSubmit('APPROVED_LOCKED')).toBe(false)
    expect(canSubmit('ARCHIVED')).toBe(false)

    expect(submitButtonLabel('EDITING')).toBe('提交审核')
    expect(submitButtonLabel('SUBMITTED_LOCKED')).toBe('审核中')
    expect(submitButtonLabel('APPROVED_LOCKED')).toBe('已通过')

    // 徽章颜色靠 class 区分，不能几个状态共用一个
    const tones = ['EDITING', 'SUBMITTED_LOCKED', 'APPROVED_LOCKED', 'ARCHIVED'].map((state) =>
      stateTone(state as Draft['state']),
    )
    expect(new Set(tones).size).toBe(4)
  })

  it('提交成功后就地改成「审核中」，不改原列表', () => {
    const input = [draft('d-001', 'EDITING'), draft('d-002', 'EDITING')]
    const next = markSubmitted(input, 'd-001')

    expect(next).not.toBe(input)
    expect(next[0].state).toBe('SUBMITTED_LOCKED')
    expect(next[1].state).toBe('EDITING')
    expect(input[0].state).toBe('EDITING')
    expect(input[0].title).toBe('草稿 d-001')
  })

  it('退回理由取最近一条 review_request_changes 的 payload.reason', () => {
    const items: Schemas['Notification'][] = [
      { id: 'n-1', type: 'review_approved', payload: { reason: '已通过' }, created_at: '2026-05-20T01:00:00Z' },
      {
        id: 'n-2',
        type: 'review_request_changes',
        payload: { reason: '旧的退回理由' },
        created_at: '2026-05-21T01:00:00Z',
      },
      {
        id: 'n-3',
        type: 'review_request_changes',
        payload: { reason: '第 2 天安排太满' },
        created_at: '2026-05-22T01:00:00Z',
      },
    ]

    expect(latestReviewReason(items)).toBe('第 2 天安排太满')
    expect(latestReviewReason([])).toBeNull()
    expect(latestReviewReason([{ type: 'review_approved', payload: { reason: '通过' } }])).toBeNull()
    expect(
      latestReviewReason([{ type: 'review_request_changes', payload: { reason: 42 } }]),
    ).toBeNull()
    expect(
      latestReviewReason([{ type: 'review_request_changes', payload: { reason: '   ' } }]),
    ).toBeNull()
  })

  it('费用按分换元展示，缺价节点单独标注', () => {
    expect(draftCostLabel({ currency: 'CNY', min_total: 0, max_total: 3400 })).toBe('¥0-¥34')
    expect(draftCostLabel({ currency: 'CNY', min_total: 200, max_total: 200, unknown_count: 2 })).toBe(
      '¥2（2 个节点待核价）',
    )
    expect(draftCostLabel(undefined)).toBe('费用待核实')

    expect(nodeCountLabel([{}, {}])).toBe('2 个节点')
    expect(nodeCountLabel([])).toBe('还没有节点')
  })
})
