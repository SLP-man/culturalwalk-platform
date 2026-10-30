/**
 * 假数据 · 账号、草稿、提交、审核队列、规划结果、通知。
 * mock 模式下这些对象在内存里被 handlers.ts 直接修改，刷新页面即恢复。
 */

import type { Schemas } from '@/api/types'

import { PLACES, PLACE_MAP } from './places'
import { ROUTES, ROUTE_MAP } from './routes'

type User = Schemas['User']
type UserProfile = Schemas['UserProfile']
type RouteDraft = Schemas['RouteDraft']
type RouteDraftDetail = Schemas['RouteDraftDetail']
type Submission = Schemas['Submission']
type ReviewTask = Schemas['ReviewTask']
type PlanDetail = Schemas['PlanDetail']
type PlanInput = Schemas['PlanInput']
type Notification = Schemas['Notification']
type CostSummary = Schemas['CostSummary']
type DraftNode = NonNullable<RouteDraftDetail['nodes']>[number]

export const DEMO_PASSWORD = 'cw123456'

export const USERS: User[] = [
  {
    id: 'u-001',
    username: '文化漫步者',
    role: 'user',
    bio: '在长沙住了七年，喜欢走没有名字的巷子。',
    created_at: '2025-11-02T03:00:00Z',
  },
  {
    id: 'u-900',
    username: '审核编辑',
    role: 'admin',
    bio: '平台编辑部，负责路线审核与发布。',
    created_at: '2025-08-01T03:00:00Z',
  },
  {
    id: 'u-002',
    username: '橘子洲头看日出',
    role: 'user',
    bio: '',
    created_at: '2026-01-14T03:00:00Z',
  },
]

export const USER_MAP: Record<string, User> = Object.fromEntries(
  USERS.map((user) => [user.id, user]),
)

export function makeId(prefix: string): string {
  return prefix + '-' + Math.random().toString(36).slice(2, 8)
}

function costOf(nodes: DraftNode[]): CostSummary {
  let min = 0
  let max = 0
  let unknown = 0
  for (const node of nodes) {
    if (node.price_min == null && node.price_max == null) {
      unknown += 1
      continue
    }
    min += node.price_min ?? node.price_max ?? 0
    max += node.price_max ?? node.price_min ?? 0
  }
  return { min_total: min, max_total: max, currency: 'CNY', unknown_count: unknown }
}

export const DRAFTS: RouteDraft[] = [
  {
    id: 'd-001',
    title: '城南旧事：第一师范与白沙井',
    summary: '沿书院路一路向南，看近代教育与市井取水两件事怎么挨在一起。',
    state: 'EDITING',
    lock_version: 4,
    base_version_id: null,
    updated_at: '2026-06-01T09:20:00Z',
  },
  {
    id: 'd-002',
    title: '雨天备选：博物院与城墙',
    summary: '室内为主，雨停时补一段城墙。',
    state: 'EDITING',
    lock_version: 2,
    base_version_id: null,
    updated_at: '2026-05-30T02:10:00Z',
  },
  {
    id: 'd-003',
    title: '老街巷里的长沙（第二版）',
    summary: '在原有街巷线上补了开福寺与斋饭时间。',
    state: 'SUBMITTED_LOCKED',
    lock_version: 7,
    base_version_id: 'v-r-laocheng-3',
    updated_at: '2026-05-28T07:45:00Z',
  },
]

export const DRAFT_MAP: Record<string, RouteDraft> = Object.fromEntries(
  DRAFTS.map((draft) => [draft.id, draft]),
)

export const DRAFT_NODES: Record<string, DraftNode[]> = {
  'd-001': [
    { position: 1, place: PLACE_MAP['p-diyishifan'], stay_minutes: 60, transport: 'walk', note: '校史馆周三下午开放。', price_min: 0, price_max: 0 },
    { position: 2, place: PLACE_MAP['p-baishajing'], stay_minutes: 25, transport: 'walk', note: null, price_min: 0, price_max: 0 },
    { position: 3, place: PLACE_MAP['p-taiping'], stay_minutes: 50, transport: 'bus', note: '傍晚人多。', price_min: 200, price_max: 200 },
  ],
  'd-002': [
    { position: 1, place: PLACE_MAP['p-museum'], stay_minutes: 150, transport: 'metro', note: '需预约，周一闭馆。', price_min: 0, price_max: 0 },
    { position: 2, place: PLACE_MAP['p-tianxinge'], stay_minutes: 50, transport: 'taxi', note: null, price_min: 3200, price_max: 3200 },
  ],
  'd-003': [
    { position: 1, place: PLACE_MAP['p-taiping'], stay_minutes: 60, transport: 'walk', note: null, price_min: 0, price_max: 0 },
    { position: 2, place: PLACE_MAP['p-chaozong'], stay_minutes: 45, transport: 'walk', note: null, price_min: 0, price_max: 0 },
    { position: 3, place: PLACE_MAP['p-kaifusi'], stay_minutes: 40, transport: 'bus', note: '斋饭 11:00 开。', price_min: 200, price_max: 200 },
  ],
}

export function draftDetail(id: string): RouteDraftDetail | null {
  const draft = DRAFT_MAP[id]
  if (!draft) return null
  const nodes = DRAFT_NODES[id] ?? []
  return { ...draft, nodes: nodes.map((node) => ({ ...node })), cost: costOf(nodes) }
}

export const SUBMISSIONS: Submission[] = [
  {
    id: 's-001',
    version_id: 'v-d-003-1',
    content_hash: 'sha256:mock-s001',
    state: 'PENDING_REVIEW',
    note: null,
    created_at: '2026-05-28T07:46:00Z',
  },
  {
    id: 's-002',
    version_id: 'v-d-004-1',
    content_hash: 'sha256:mock-s002',
    state: 'CHANGES_REQUESTED',
    note: '第 2 天安排太满，建议把开福寺挪到第 1 天下午，并补上每段的交通耗时。',
    created_at: '2026-05-22T03:30:00Z',
  },
  {
    id: 's-003',
    route_id: 'r-jiangbian',
    version_id: 'v-r-jiangbian-1',
    content_hash: 'sha256:mock-s003',
    state: 'APPROVED',
    note: '已通过，发布于 2026-05-20。',
    created_at: '2026-05-19T02:00:00Z',
  },
]

export const SUBMISSION_MAP: Record<string, Submission> = Object.fromEntries(
  SUBMISSIONS.map((submission) => [submission.id, submission]),
)

/** FE-06 用：草稿 + 它最新一次提交（提交后按钮应变成“审核中”）。 */
export const DRAFT_SUBMISSION: Record<string, string> = {
  'd-003': 's-001',
}

export const REVIEW_TASKS: ReviewTask[] = [
  {
    id: 't-001',
    submission_id: 's-001',
    state: 'OPEN',
    assignee_id: null,
    lease_expires_at: null,
    completed_action: null,
    created_at: '2026-05-28T07:46:00Z',
  },
  {
    id: 't-002',
    submission_id: 's-002',
    state: 'COMPLETED',
    assignee_id: 'u-900',
    lease_expires_at: null,
    completed_action: 'request_changes',
    created_at: '2026-05-22T03:30:00Z',
  },
  {
    id: 't-003',
    submission_id: 's-003',
    state: 'COMPLETED',
    assignee_id: 'u-900',
    lease_expires_at: null,
    completed_action: 'approve',
    created_at: '2026-05-19T02:00:00Z',
  },
]

export interface ReviewQueueItem {
  task: ReviewTask
  submission: Submission
  routeTitle: string
  authorName: string
  /** 提交快照里被改动的文本，用于 FE-08 的 diff 视图 */
  before: string
  after: string
}

export const REVIEW_QUEUE: ReviewQueueItem[] = [
  {
    task: REVIEW_TASKS[0],
    submission: SUBMISSIONS[0],
    routeTitle: '老街巷里的长沙（第二版）',
    authorName: '文化漫步者',
    before:
      '太平老街 60 分钟 → 潮宗街 45 分钟（步行）',
    after:
      '太平老街 60 分钟 → 潮宗街 45 分钟（步行）→ 开福寺 40 分钟（公交 15 分钟，斋饭 11:00 开）',
  },
  {
    task: REVIEW_TASKS[1],
    submission: SUBMISSIONS[1],
    routeTitle: '两日亲子：书院与江滩',
    authorName: '文化漫步者',
    before:
      '第 2 天：湖南博物院 150 分钟 → 天心阁 50 分钟 → 白沙古井 25 分钟',
    after:
      '第 1 天：岳麓书院 90 分钟 → 爱晚亭 40 分钟 → 橘子洲头 60 分钟\n第 2 天：湖南博物院 150 分钟 → 天心阁 50 分钟',
  },
  {
    task: REVIEW_TASKS[2],
    submission: SUBMISSIONS[2],
    routeTitle: '湘江边的傍晚散步',
    authorName: '文化漫步者',
    before: '（首次提交，无上一版）',
    after: '橘子洲头 60 分钟 → 湘江中路步行 40 分钟，总价 3-6 元',
  },
]

export const NOTIFICATIONS: Notification[] = [
  {
    id: 'n-001',
    type: 'review_request_changes',
    payload: { reason: SUBMISSIONS[1].note, title: '两日亲子：书院与江滩' },
    read_at: null,
    created_at: '2026-05-22T03:31:00Z',
  },
  {
    id: 'n-002',
    type: 'review_approved',
    payload: { title: '湘江边的傍晚散步' },
    read_at: '2026-05-20T01:00:00Z',
    created_at: '2026-05-19T06:00:00Z',
  },
]

export function buildProfile(userId: string): UserProfile | null {
  const user = USER_MAP[userId]
  if (!user) return null
  return {
    user,
    published_routes: ROUTES.filter((route) => route.author?.id === userId),
    comment_count: user.id === 'u-001' ? 2 : 0,
  }
}

export function buildPlan(input: PlanInput): PlanDetail {
  const days = Math.max(1, Math.min(input.days, 7))
  const perDay = input.pace === 'packed' ? 4 : input.pace === 'relaxed' ? 2 : 3
  const daysPlan = Array.from({ length: days }, (_, dayIndex) => {
    const items = Array.from({ length: perDay }, (_, i) => {
      const place = PLACES[(dayIndex * perDay + i) % PLACES.length]
      return {
        order: i + 1,
        place,
        stay_minutes: 60,
        transport: (input.transport?.[0] ?? 'walk') as string,
        price_min: 0,
        price_max: 4000,
        confidence: 'likely' as const,
        reason: '按你选的「' + (input.themes?.join('、') ?? '历史文化') + '」主题匹配，离上一个点步行 12 分钟。',
      }
    })
    return { day_index: dayIndex + 1, items }
  })
  const nights = Math.max(0, days - 1)
  return {
    id: makeId('plan'),
    state: 'READY',
    city: input.city,
    days,
    people: input.people,
    budget_total: input.budget_total,
    share_token: null,
    error_code: null,
    created_at: new Date().toISOString(),
    steps: [
      { agent: 'researcher', status: 'done', duration_ms: 1200 },
      { agent: 'planner', status: 'done', duration_ms: 2400 },
      { agent: 'critic', status: 'done', duration_ms: 900 },
      { agent: 'verifier', status: 'done', duration_ms: 700 },
    ],
    cost: {
      min_total: days * 4000 + (input.include_lodging ? nights * 25000 : 0),
      max_total: days * 9000 + (input.include_lodging ? nights * 45000 : 0),
      currency: 'CNY',
      unknown_count: 0,
    },
    days_plan: daysPlan,
  }
}

export const PUBLISHED_LOOKUP = ROUTE_MAP
