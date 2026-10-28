/**
 * 浏览页的筛选逻辑。抽成纯函数，方便单测，也让页面只负责状态与渲染。
 */

export type BrowseFilters = {
  q: string
  theme: string
  duration: string
  channel: string
}

export const EMPTY_FILTERS: BrowseFilters = { q: '', theme: '', duration: '', channel: '' }

/** 时长区间取值与接口契约一致：0-120 / 120-240 / 240- */
export const DURATION_OPTIONS = [
  { value: '', label: '全部时长' },
  { value: '0-120', label: '2 小时以内' },
  { value: '120-240', label: '2-4 小时' },
  { value: '240-', label: '4 小时以上' },
] as const

export const CHANNEL_OPTIONS = [
  { value: '', label: '全部来源' },
  { value: 'official', label: '官方' },
  { value: 'user', label: '用户投稿' },
] as const

export const THEME_LIMIT = 10

export function hasActiveFilter(filters: BrowseFilters): boolean {
  return Boolean(filters.q.trim() || filters.theme || filters.duration || filters.channel)
}

/** 空值不下发，避免 ?theme=&duration= 这类噪声；limit 总是带。 */
export function buildRouteQuery(
  filters: BrowseFilters,
  cursor: string | null,
  limit: number,
): string {
  const params = new URLSearchParams()
  const q = filters.q.trim()
  if (q) params.set('q', q)
  if (filters.theme) params.set('theme', filters.theme)
  if (filters.duration) params.set('duration', filters.duration)
  if (filters.channel) params.set('channel', filters.channel)
  if (cursor) params.set('cursor', cursor)
  params.set('limit', String(limit))
  return params.toString()
}

/**
 * 把已加载路线的 theme_tags 汇总成筛选 chip：出现次数多的在前，最多 10 个。
 * 已选中的主题一定保留，否则选完之后 chip 消失，用户无法取消选择。
 */
export function rankThemes(
  pool: readonly string[],
  selected = '',
  limit = THEME_LIMIT,
): string[] {
  const counts = new Map<string, number>()
  const firstSeen: string[] = []
  for (const tag of pool) {
    if (!tag) continue
    if (!counts.has(tag)) firstSeen.push(tag)
    counts.set(tag, (counts.get(tag) ?? 0) + 1)
  }
  const ranked = [...firstSeen].sort((a, b) => (counts.get(b) ?? 0) - (counts.get(a) ?? 0))
  if (!selected) return ranked.slice(0, limit)
  const others = ranked.filter((tag) => tag !== selected)
  return [selected, ...others].slice(0, limit)
}
