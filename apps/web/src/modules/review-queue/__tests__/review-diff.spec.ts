import { describe, expect, it } from 'vitest'

import {
  MAX_DIFF_LINES,
  diffLines,
  snapshotText,
  splitLines,
  toDiffRows,
} from '../diff'
import {
  decisionBlockedReason,
  isPendingTask,
  reviewTaskStateLabel,
  type ReviewDecision,
} from '../state'

function kinds(before: string, after: string): string[] {
  return diffLines(before, after).ops.map((op) => op.kind)
}

describe('splitLines', () => {
  it('统一换行并丢掉结尾的空行', () => {
    expect(splitLines('a\r\nb\n')).toEqual(['a', 'b'])
    expect(splitLines('')).toEqual([])
    expect(splitLines(null)).toEqual([])
  })
})

describe('diffLines', () => {
  it('文本不变时全部标为 same', () => {
    const result = diffLines('第一行\n第二行', '第一行\n第二行')
    expect(result.ops.map((op) => op.kind)).toEqual(['same', 'same'])
    expect(result.truncated).toBe(false)
    expect(result.ops[1]).toEqual({ kind: 'same', text: '第二行', leftNo: 2, rightNo: 2 })
  })

  it('追加一行只产生一条新增，行号落在右栏', () => {
    const result = diffLines('旧内容', '旧内容\n新内容')
    expect(result.ops.map((op) => op.kind)).toEqual(['same', 'add'])
    expect(result.ops[1].leftNo).toBeNull()
    expect(result.ops[1].rightNo).toBe(2)
  })

  it('删除一行只产生一条删除，行号落在左栏', () => {
    const result = diffLines('保留\n删掉', '保留')
    expect(kinds('保留\n删掉', '保留')).toEqual(['same', 'del'])
    expect(result.ops[1].leftNo).toBe(2)
    expect(result.ops[1].rightNo).toBeNull()
  })

  it('上一版为空时全部按新增算', () => {
    expect(kinds('', '甲\n乙')).toEqual(['add', 'add'])
    expect(kinds('甲\n乙', '')).toEqual(['del', 'del'])
  })

  it('改一行得到一条删除加一条新增', () => {
    expect(kinds('甲\n乙\n丙', '甲\n乙改\n丙')).toEqual(['same', 'del', 'add', 'same'])
  })

  it('超过 200 行截断并给出总行数', () => {
    const before = Array.from({ length: 300 }, (_, index) => 'old-' + index).join('\n')
    const after = Array.from({ length: 300 }, (_, index) => 'new-' + index).join('\n')
    const result = diffLines(before, after)
    expect(MAX_DIFF_LINES).toBe(200)
    expect(result.ops).toHaveLength(MAX_DIFF_LINES)
    expect(result.totalOps).toBe(600)
    expect(result.truncated).toBe(true)
  })
})

describe('toDiffRows', () => {
  it('删除只落左栏，新增只落右栏', () => {
    const rows = toDiffRows(diffLines('甲', '乙').ops)
    expect(rows).toHaveLength(2)
    expect(rows[0].left).toEqual({ no: 1, text: '甲' })
    expect(rows[0].right).toBeNull()
    expect(rows[1].left).toBeNull()
    expect(rows[1].right).toEqual({ no: 1, text: '乙' })
  })

  it('same 行两侧的文本一致', () => {
    const [row] = toDiffRows(diffLines('同一行', '同一行').ops)
    expect(row.kind).toBe('same')
    expect(row.left).toEqual(row.right)
  })
})

describe('snapshotText', () => {
  it('只取字符串字段，缺失时返回空串', () => {
    expect(snapshotText({ title: '老街巷', content: '甲 → 乙' }, 'content')).toBe('甲 → 乙')
    expect(snapshotText({ title: 1 }, 'title')).toBe('')
    expect(snapshotText(null, 'content')).toBe('')
  })
})

describe('reviewTaskStateLabel', () => {
  it('四个状态各有中文文案', () => {
    expect(reviewTaskStateLabel('OPEN')).toBe('待领取')
    expect(reviewTaskStateLabel('CLAIMED')).toBe('审核中')
    expect(reviewTaskStateLabel('COMPLETED')).toBe('已完成')
    expect(reviewTaskStateLabel('CANCELLED')).toBe('已取消')
  })

  it('空值和未知状态不炸', () => {
    expect(reviewTaskStateLabel(null)).toBe('')
    expect(reviewTaskStateLabel('WEIRD')).toBe('WEIRD')
  })
})

describe('isPendingTask', () => {
  it('只有 OPEN / CLAIMED 还在待审', () => {
    expect(isPendingTask({ id: 't-1', state: 'OPEN' })).toBe(true)
    expect(isPendingTask({ id: 't-2', state: 'CLAIMED' })).toBe(true)
    expect(isPendingTask({ id: 't-3', state: 'COMPLETED' })).toBe(false)
    expect(isPendingTask({ id: 't-4', state: 'CANCELLED' })).toBe(false)
  })
})

describe('decisionBlockedReason', () => {
  const cases: Array<[ReviewDecision | null, string, string]> = [
    ['request_changes', '', '退回必须写理由'],
    ['request_changes', '   ', '退回必须写理由'],
    ['request_changes', '请补上开放时间', ''],
    ['approve', '', ''],
    [null, '', ''],
  ]

  it.each(cases)('action=%s note=%j 时提示应为 %j', (action, note, expected) => {
    expect(decisionBlockedReason(action, note)).toBe(expected)
  })
})
