/**
 * 审核 diff：把两段文本按行做 LCS 对齐，产出逐行差异。
 * 纯函数，便于单测；页面和组件只负责渲染。
 */

export type DiffKind = 'same' | 'add' | 'del'

export interface DiffOp {
  /** same 表示两侧都有；add 只有右栏，del 只有左栏 */
  kind: DiffKind
  text: string
  leftNo: number | null
  rightNo: number | null
}

export interface DiffResult {
  /** 已按 limit 截断的差异行 */
  ops: DiffOp[]
  /** 截断前的总行数，用于提示 */
  totalOps: number
  truncated: boolean
}

export interface DiffRow {
  key: string
  kind: DiffKind
  left: { no: number; text: string } | null
  right: { no: number; text: string } | null
}

/** 一屏最多画多少行，再多也看不清 */
export const MAX_DIFF_LINES = 200

/** LCS 是 O(n×m)，超长文本先砍掉，别把主线程算死 */
const MAX_INPUT_LINES = 400

export function splitLines(text: string | null | undefined): string[] {
  if (!text) return []
  const lines = text.replace(/\r\n?/g, '\n').split('\n')
  // 末尾的换行不算一行空内容
  while (lines.length > 0 && lines[lines.length - 1] === '') lines.pop()
  return lines
}

export function diffLines(
  before: string | null | undefined,
  after: string | null | undefined,
  limit: number = MAX_DIFF_LINES,
): DiffResult {
  const left = splitLines(before).slice(0, MAX_INPUT_LINES)
  const right = splitLines(after).slice(0, MAX_INPUT_LINES)
  const table = buildLcsTable(left, right)

  const ops: DiffOp[] = []
  let i = 0
  let j = 0
  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      ops.push({ kind: 'same', text: left[i], leftNo: i + 1, rightNo: j + 1 })
      i += 1
      j += 1
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      ops.push({ kind: 'del', text: left[i], leftNo: i + 1, rightNo: null })
      i += 1
    } else {
      ops.push({ kind: 'add', text: right[j], leftNo: null, rightNo: j + 1 })
      j += 1
    }
  }
  while (i < left.length) {
    ops.push({ kind: 'del', text: left[i], leftNo: i + 1, rightNo: null })
    i += 1
  }
  while (j < right.length) {
    ops.push({ kind: 'add', text: right[j], leftNo: null, rightNo: j + 1 })
    j += 1
  }

  return { ops: ops.slice(0, limit), totalOps: ops.length, truncated: ops.length > limit }
}

function buildLcsTable(left: string[], right: string[]): number[][] {
  const table: number[][] = Array.from({ length: left.length + 1 }, () =>
    new Array<number>(right.length + 1).fill(0),
  )
  for (let i = left.length - 1; i >= 0; i -= 1) {
    for (let j = right.length - 1; j >= 0; j -= 1) {
      table[i][j] =
        left[i] === right[j]
          ? table[i + 1][j + 1] + 1
          : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }
  return table
}

/** 转成两栏对照的行：删除只落左栏，新增只落右栏 */
export function toDiffRows(ops: DiffOp[]): DiffRow[] {
  return ops.map((op, index) => ({
    key: index + '-' + op.kind,
    kind: op.kind,
    left: op.leftNo == null ? null : { no: op.leftNo, text: op.text },
    right: op.rightNo == null ? null : { no: op.rightNo, text: op.text },
  }))
}

/** 快照是 { [key: string]: unknown }，取值前先确认是字符串 */
export function snapshotText(
  snapshot: Record<string, unknown> | null | undefined,
  key: string,
): string {
  const value = snapshot?.[key]
  return typeof value === 'string' ? value : ''
}
