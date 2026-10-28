/**
 * 展示层格式化。金额一律以“分”为单位存，展示时才换成元。
 */

const TRANSPORT_LABEL: Record<string, string> = {
  walk: '步行',
  metro: '地铁',
  bus: '公交',
  taxi: '打车',
  bike: '骑行',
}

const CONFIDENCE_LABEL: Record<string, string> = {
  verified: '已核实',
  likely: '较可信',
  unverified: '待核实',
}

const DRAFT_STATE_LABEL: Record<string, string> = {
  EDITING: '编辑中',
  SUBMITTED_LOCKED: '审核中',
  APPROVED_LOCKED: '已通过',
  ARCHIVED: '已归档',
}

const SUBMISSION_STATE_LABEL: Record<string, string> = {
  PENDING_REVIEW: '审核中',
  CHANGES_REQUESTED: '已退回',
  REJECTED: '未通过',
  APPROVED: '已通过',
  WITHDRAWN: '已撤回',
  SUPERSEDED: '已被新版替代',
}

const REVIEW_ACTION_LABEL: Record<string, string> = {
  approve: '通过',
  request_changes: '退回修改',
  reject: '不通过',
}

export function money(fen: number | null | undefined): string {
  if (fen == null) return '价格待核实'
  const yuan = fen / 100
  return '¥' + (Number.isInteger(yuan) ? String(yuan) : yuan.toFixed(1))
}

export function moneyRange(min: number | null | undefined, max: number | null | undefined): string {
  if (min == null && max == null) return '价格待核实'
  if (min != null && max != null && min !== max) return money(min) + '-' + money(max)
  return money(max ?? min)
}

export function durationLabel(minutes: number | null | undefined): string {
  if (minutes == null) return '时长待定'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours) return rest + ' 分钟'
  if (!rest) return hours + ' 小时'
  return hours + ' 小时 ' + rest + ' 分'
}

export function transportLabel(value: string | null | undefined): string {
  if (!value) return '步行'
  return TRANSPORT_LABEL[value] ?? value
}

export function confidenceLabel(value: string | null | undefined): string {
  if (!value) return '待核实'
  return CONFIDENCE_LABEL[value] ?? value
}

export function draftStateLabel(value: string | null | undefined): string {
  if (!value) return ''
  return DRAFT_STATE_LABEL[value] ?? value
}

export function submissionStateLabel(value: string | null | undefined): string {
  if (!value) return ''
  return SUBMISSION_STATE_LABEL[value] ?? value
}

export function reviewActionLabel(value: string | null | undefined): string {
  if (!value) return '待处理'
  return REVIEW_ACTION_LABEL[value] ?? value
}

export function channelLabel(value: string | null | undefined): string {
  return value === 'official' ? '官方' : '用户投稿'
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  const diff = Date.now() - then
  const minute = 60 * 1000
  if (diff < minute) return '刚刚'
  if (diff < 60 * minute) return Math.floor(diff / minute) + ' 分钟前'
  if (diff < 24 * 60 * minute) return Math.floor(diff / (60 * minute)) + ' 小时前'
  return shortDate(iso)
}
