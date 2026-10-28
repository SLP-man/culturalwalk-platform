import { describe, expect, it } from 'vitest'

import type { Schemas } from '@/api/types'

import { sortComments } from '../logic'

type Comment = Schemas['Comment']

function comment(partial: Partial<Comment>): Comment {
  return { id: 'c-1', body: '内容', pinned: false, created_at: '2026-05-01T00:00:00Z', ...partial }
}

describe('sortComments', () => {
  it('置顶评论排最前，其余按时间倒序', () => {
    const sorted = sortComments([
      comment({ id: 'c-old', created_at: '2026-05-01T00:00:00Z' }),
      comment({ id: 'c-pinned', pinned: true, created_at: '2026-04-01T00:00:00Z' }),
      comment({ id: 'c-new', created_at: '2026-05-20T00:00:00Z' }),
    ])
    expect(sorted.map((entry) => entry.id)).toEqual(['c-pinned', 'c-new', 'c-old'])
  })

  it('没有 created_at 的排最后，且不改动入参数组', () => {
    const input = [
      comment({ id: 'c-none', created_at: undefined }),
      comment({ id: 'c-has', created_at: '2026-05-20T00:00:00Z' }),
    ]
    expect(sortComments(input).map((entry) => entry.id)).toEqual(['c-has', 'c-none'])
    expect(input.map((entry) => entry.id)).toEqual(['c-none', 'c-has'])
  })

  it('空数组原样返回', () => {
    expect(sortComments([])).toEqual([])
  })
})
