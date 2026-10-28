/**
 * 假数据分发器。仅在 USE_MOCK 时被 shared/api.ts 调用，接口就绪后关开关即可。
 *
 * 只在内存里改数据：刷新页面恢复初始 fixtures（前端演示够用，也不需要后端）。
 */

import type { Schemas } from '@/api/types'

import { PLACES, PLACE_MAP } from './places'
import { COMMENTS, ROUTES, buildRouteDetail } from './routes'
import {
  DEMO_PASSWORD,
  DRAFTS,
  DRAFT_NODES,
  NOTIFICATIONS,
  REVIEW_QUEUE,
  REVIEW_TASKS,
  SUBMISSIONS,
  USERS,
  USER_MAP,
  buildPlan,
  buildProfile,
  makeId,
} from './workspace'

type Comment = Schemas['Comment']
type Notification = Schemas['Notification']
type Place = Schemas['Place']
type PlanInput = Schemas['PlanInput']
type ReviewTask = Schemas['ReviewTask']
type RouteDraft = Schemas['RouteDraft']
type RouteDraftDetail = Schemas['RouteDraftDetail']
type RouteSummary = Schemas['RouteSummary']
type Submission = Schemas['Submission']
type TokenPair = Schemas['TokenPair']
type User = Schemas['User']

export class MockError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'MockError'
  }
}

const TOKEN_PREFIX = 'mock-token:'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function tokenFor(userId: string): string {
  return TOKEN_PREFIX + userId
}

function userFromToken(token: string | null): User | null {
  if (!token || !token.startsWith(TOKEN_PREFIX)) return null
  return USER_MAP[token.slice(TOKEN_PREFIX.length)] ?? null
}

function tokenPair(user: User): TokenPair {
  return {
    access_token: tokenFor(user.id),
    refresh_token: tokenFor(user.id),
    expires_in: 7200,
    user,
  }
}

/* ---------------- 内存状态（刷新即还原） ---------------- */

const state = {
  routes: [...ROUTES],
  comments: [...COMMENTS],
  drafts: [...DRAFTS],
  draftNodes: JSON.parse(JSON.stringify(DRAFT_NODES)) as typeof DRAFT_NODES,
  submissions: [...SUBMISSIONS],
  reviewTasks: REVIEW_TASKS.map((task) => ({ ...task })),
  notifications: [...NOTIFICATIONS],
  favorites: new Set<string>(),
  plans: new Map<string, Schemas['PlanDetail']>(),
}

function costOf(nodes: NonNullable<RouteDraftDetail['nodes']>) {
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

function findDraft(id: string): RouteDraft | undefined {
  return state.drafts.find((draft) => draft.id === id)
}

function requireDraft(id: string): RouteDraft {
  const draft = findDraft(id)
  if (!draft) throw new MockError(404, 'DRAFT_NOT_FOUND', '草稿不存在')
  return draft
}

function editable(draft: RouteDraft): void {
  if (draft.state !== 'EDITING') {
    throw new MockError(409, 'DRAFT_LOCKED', '草稿已提交审核，不能再改')
  }
}

function draftWithNodes(id: string): RouteDraftDetail {
  const draft = requireDraft(id)
  const nodes = state.draftNodes[id] ?? []
  return { ...draft, nodes: nodes.map((node) => ({ ...node })), cost: costOf(nodes) }
}

function nowIso(): string {
  return new Date().toISOString()
}

function bump(draft: RouteDraft): void {
  draft.lock_version += 1
  draft.updated_at = nowIso()
}

function durationIn(range: string, minutes: number | null | undefined): boolean {
  if (minutes == null) return false
  const [from, to] = range.split('-')
  const lo = Number(from || 0)
  const hi = to ? Number(to) : Number.POSITIVE_INFINITY
  return minutes >= lo && minutes <= hi
}

function filteredRoutes(query: URLSearchParams): RouteSummary[] {
  const q = (query.get('q') ?? '').trim().toLowerCase()
  const theme = query.get('theme') ?? ''
  const duration = query.get('duration') ?? ''
  const channel = query.get('channel') ?? ''
  return state.routes.filter((route) => {
    if (theme && !(route.theme_tags ?? []).includes(theme)) return false
    if (channel && route.channel !== channel) return false
    if (duration && !durationIn(duration, route.duration_minutes)) return false
    if (q) {
      const hay = (route.title + ' ' + (route.summary ?? '') + ' ' + (route.theme_tags ?? []).join(' ')).toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
}

/* ---------------- 路由表 ---------------- */

interface Ctx {
  query: URLSearchParams
  body: Record<string, unknown>
  user: User | null
}

type Handler = (ctx: Ctx, params: Record<string, string>) => unknown | Promise<unknown>

const table: Array<[string, string, Handler]> = [
  ['POST', '/auth/register', ({ body }) => {
    const username = String(body.username ?? '').trim()
    const password = String(body.password ?? '')
    if (username.length < 2) throw new MockError(422, 'VALIDATION_FAILED', '用户名至少 2 个字')
    if (password.length < 6) throw new MockError(422, 'VALIDATION_FAILED', '密码至少 6 位')
    const existing = USERS.find((user) => user.username === username)
    if (existing) throw new MockError(409, 'USERNAME_TAKEN', '这个用户名已经被用了')
    const user: User = { id: makeId('u'), username, role: 'user', bio: '', created_at: nowIso() }
    USERS.push(user)
    USER_MAP[user.id] = user
    return tokenPair(user)
  }],

  ['POST', '/auth/login', ({ body }) => {
    const username = String(body.username ?? '').trim()
    const password = String(body.password ?? '')
    const user = USERS.find((item) => item.username === username)
    if (!user || (password !== DEMO_PASSWORD && password !== 'admin123')) {
      throw new MockError(401, 'INVALID_CREDENTIALS', '用户名或密码不对（演示密码 cw123456）')
    }
    return tokenPair(user)
  }],

  ['POST', '/auth/refresh', ({ body }) => {
    const user = userFromToken(String(body.refresh_token ?? ''))
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '登录已失效，请重新登录')
    return tokenPair(user)
  }],

  ['POST', '/auth/logout', () => undefined],

  ['GET', '/users/me', ({ user }) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '请先登录')
    return user
  }],

  ['GET', '/users/:user_id/profile', (_ctx, params) => {
    const profile = buildProfile(params.user_id)
    if (!profile) throw new MockError(404, 'USER_NOT_FOUND', '用户不存在')
    return profile
  }],

  ['GET', '/places', ({ query }) => {
    const q = (query.get('q') ?? '').trim()
    const items: Place[] = q ? PLACES.filter((place) => place.name.includes(q)) : PLACES
    return { items, next_cursor: null }
  }],

  ['GET', '/places/:place_id', (_ctx, params) => {
    const place = PLACE_MAP[params.place_id]
    if (!place) throw new MockError(404, 'PLACE_NOT_FOUND', '地点不存在')
    return place
  }],

  ['GET', '/routes', ({ query }) => {
    const limit = Math.max(1, Math.min(Number(query.get('limit') ?? 20), 50))
    const offset = Number(query.get('cursor') ?? 0) || 0
    const all = filteredRoutes(query)
    const items = all.slice(offset, offset + limit)
    const next = offset + limit < all.length ? String(offset + limit) : null
    return { items, next_cursor: next }
  }],

  ['GET', '/routes/:route_id', ({ user }, params) => {
    const detail = buildRouteDetail(params.route_id)
    if (!detail) throw new MockError(404, 'ROUTE_NOT_FOUND', '路线不存在')
    return { ...detail, is_favorited: state.favorites.has(params.route_id), comment_count: state.comments.filter((c) => c.route_id === params.route_id).length || detail.comment_count, viewer: user ? user.username : null }
  }],

  ['GET', '/routes/:route_id/comments', (_ctx, params) => {
    const items = state.comments
      .filter((comment) => comment.route_id === params.route_id)
      .sort((a, b) => Number(b.pinned) - Number(a.pinned))
    return { items, next_cursor: null, total: items.length }
  }],

  ['POST', '/routes/:route_id/comments', ({ body, user }, params) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '登录后才能评论')
    const text = String(body.body ?? '').trim()
    if (!text) throw new MockError(422, 'VALIDATION_FAILED', '评论不能为空')
    const comment: Comment = {
      id: makeId('c'),
      route_id: params.route_id,
      body: text,
      pinned: false,
      author: { id: user.id, username: user.username },
      created_at: nowIso(),
    }
    state.comments.unshift(comment)
    return comment
  }],

  ['POST', '/comments/:comment_id/pin', (_ctx, params) => {
    const comment = state.comments.find((item) => item.id === params.comment_id)
    if (!comment) throw new MockError(404, 'COMMENT_NOT_FOUND', '评论不存在')
    for (const item of state.comments) {
      if (item.route_id === comment.route_id) item.pinned = false
    }
    comment.pinned = true
    return comment
  }],

  ['POST', '/routes/:route_id/favorite', (_ctx, params) => {
    if (state.favorites.has(params.route_id)) state.favorites.delete(params.route_id)
    else state.favorites.add(params.route_id)
    return { is_favorited: state.favorites.has(params.route_id) }
  }],

  ['GET', '/route-drafts', ({ query, user }) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '请先登录')
    const wanted = query.get('state')
    const items: RouteDraft[] = wanted
      ? state.drafts.filter((draft) => draft.state === wanted)
      : state.drafts
    return { items, next_cursor: null }
  }],

  ['POST', '/route-drafts', ({ body, user }) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '请先登录')
    const title = String(body.title ?? '').trim()
    if (!title) throw new MockError(422, 'VALIDATION_FAILED', '先给路线起个名字')
    const draft: RouteDraft = {
      id: makeId('d'),
      title,
      summary: String(body.summary ?? ''),
      state: 'EDITING',
      lock_version: 1,
      base_version_id: null,
      updated_at: nowIso(),
    }
    state.drafts.unshift(draft)
    state.draftNodes[draft.id] = []
    return draftWithNodes(draft.id)
  }],

  ['GET', '/route-drafts/:draft_id', (_ctx, params) => draftWithNodes(params.draft_id)],

  ['PATCH', '/route-drafts/:draft_id', ({ body }, params) => {
    const draft = requireDraft(params.draft_id)
    editable(draft)
    if (typeof body.title === 'string') draft.title = body.title
    if (typeof body.summary === 'string') draft.summary = body.summary
    bump(draft)
    return draftWithNodes(draft.id)
  }],

  ['PUT', '/route-drafts/:draft_id/nodes', ({ body }, params) => {
    const draft = requireDraft(params.draft_id)
    editable(draft)
    const incoming = Array.isArray(body.nodes) ? body.nodes : []
    state.draftNodes[draft.id] = incoming.map((raw, index) => {
      const node = raw as Record<string, unknown>
      const placeId = String(node.place_id ?? '')
      return {
        position: index + 1,
        place: PLACE_MAP[placeId],
        stay_minutes: Number(node.stay_minutes ?? 60),
        transport: node.transport ? String(node.transport) : undefined,
        note: typeof node.note === 'string' ? node.note : null,
        price_min: node.price_min == null ? null : Number(node.price_min),
        price_max: node.price_max == null ? null : Number(node.price_max),
      }
    })
    bump(draft)
    return draftWithNodes(draft.id)
  }],

  ['POST', '/route-drafts/:draft_id/submit', ({ body }, params) => {
    const draft = requireDraft(params.draft_id)
    editable(draft)
    const nodes = state.draftNodes[draft.id] ?? []
    if (nodes.length < 2) throw new MockError(422, 'VALIDATION_FAILED', '至少要放 2 个节点才能提交')
    const submission: Submission = {
      id: makeId('s'),
      version_id: makeId('v'),
      content_hash: 'sha256:mock-' + draft.id,
      state: 'PENDING_REVIEW',
      note: String(body.note ?? '') || null,
      created_at: nowIso(),
    }
    state.submissions.unshift(submission)
    draft.state = 'SUBMITTED_LOCKED'
    bump(draft)
    state.reviewTasks.unshift({
      id: makeId('t'),
      submission_id: submission.id,
      state: 'OPEN',
      assignee_id: null,
      lease_expires_at: null,
      completed_action: null,
      created_at: nowIso(),
    })
    REVIEW_QUEUE.unshift({
      task: state.reviewTasks[0],
      submission,
      routeTitle: draft.title,
      authorName: '文化漫步者',
      before: '（上一版快照缺失，mock 里只展示本次内容）',
      after: nodes.map((node) => (node.place?.name ?? '未知地点') + ' ' + (node.stay_minutes ?? 60) + ' 分钟').join(' → '),
    })
    return submission
  }],

  ['GET', '/review/tasks', ({ query }) => {
    const wanted = query.get('state')
    const items = wanted
      ? state.reviewTasks.filter((task) => task.state === wanted)
      : state.reviewTasks
    return { items, next_cursor: null }
  }],

  ['POST', '/review/tasks/:task_id/claim', ({ user }, params) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '请先登录')
    const task = state.reviewTasks.find((item) => item.id === params.task_id)
    if (!task) throw new MockError(404, 'TASK_NOT_FOUND', '审核任务不存在')
    task.state = 'CLAIMED'
    task.assignee_id = user.id
    task.lease_expires_at = new Date(Date.now() + 15 * 60 * 1000).toISOString()
    return task
  }],

  ['POST', '/review/tasks/:task_id/decision', ({ body }, params) => {
    const task = state.reviewTasks.find((item) => item.id === params.task_id) as ReviewTask | undefined
    if (!task) throw new MockError(404, 'TASK_NOT_FOUND', '审核任务不存在')
    const action = String(body.action ?? '')
    const note = String(body.note ?? '').trim()
    if (action !== 'approve' && action !== 'request_changes' && action !== 'reject') {
      throw new MockError(422, 'VALIDATION_FAILED', 'action 只能是 approve / request_changes / reject')
    }
    if (action !== 'approve' && !note) {
      throw new MockError(422, 'REVIEW_REASON_REQUIRED', '退回必须写理由')
    }
    task.state = 'COMPLETED'
    task.completed_action = action
    task.lease_expires_at = null
    const submission = state.submissions.find((item) => item.id === task.submission_id)
    if (submission) {
      submission.state = action === 'approve' ? 'APPROVED' : action === 'reject' ? 'REJECTED' : 'CHANGES_REQUESTED'
      if (note) submission.note = note
      const draft = state.drafts.find((item) => item.state === 'SUBMITTED_LOCKED' && item.title && submission.version_id?.includes(item.id))
      if (draft && action !== 'approve') draft.state = 'EDITING'
    }
    state.notifications.unshift({
      id: makeId('n'),
      type: action === 'approve' ? 'review_approved' : action === 'reject' ? 'review_rejected' : 'review_request_changes',
      payload: { reason: note, task: task.id },
      read_at: null,
      created_at: nowIso(),
    })
    return task
  }],

  ['GET', '/notifications', ({ query }) => {
    const limit = Math.max(1, Math.min(Number(query.get('limit') ?? 20), 50))
    const items: Notification[] = state.notifications.slice(0, limit)
    return { items, next_cursor: null }
  }],

  ['POST', '/notifications/:notification_id/read', (_ctx, params) => {
    const found = state.notifications.find((item) => item.id === params.notification_id)
    if (!found) throw new MockError(404, 'NOTIFICATION_NOT_FOUND', '通知不存在')
    found.read_at = nowIso()
    return found
  }],

  ['POST', '/plans', async ({ body, user }) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '登录后才能生成行程')
    const input = body as unknown as PlanInput
    if (!input.city) throw new MockError(422, 'VALIDATION_FAILED', '请选择城市')
    if (!input.days || input.days < 1) throw new MockError(422, 'VALIDATION_FAILED', '天数至少 1 天')
    if (!input.people || input.people < 1) throw new MockError(422, 'VALIDATION_FAILED', '人数至少 1 人')
    await sleep(900)
    const plan = buildPlan(input)
    state.plans.set(plan.id, plan)
    return plan
  }],

  ['GET', '/plans/:plan_id', (_ctx, params) => {
    const plan = state.plans.get(params.plan_id)
    if (!plan) throw new MockError(404, 'PLAN_NOT_FOUND', '行程不存在')
    return plan
  }],

  ['POST', '/plans/:plan_id/to-draft', ({ user }, params) => {
    if (!user) throw new MockError(401, 'UNAUTHORIZED', '请先登录')
    const plan = state.plans.get(params.plan_id)
    if (!plan) throw new MockError(404, 'PLAN_NOT_FOUND', '行程不存在')
    const firstDay = plan.days_plan?.[0]?.items ?? []
    const draft: RouteDraft = {
      id: makeId('d'),
      title: plan.city + ' ' + (plan.days ?? 1) + ' 日行程',
      summary: '由规划助手生成，可直接继续编辑。',
      state: 'EDITING',
      lock_version: 1,
      base_version_id: null,
      updated_at: nowIso(),
    }
    state.drafts.unshift(draft)
    state.draftNodes[draft.id] = firstDay.map((item, index) => ({
      position: index + 1,
      place: item.place,
      stay_minutes: item.stay_minutes ?? 60,
      transport: item.transport ?? 'walk',
      note: null,
      price_min: item.price_min ?? null,
      price_max: item.price_max ?? null,
    }))
    return draftWithNodes(draft.id)
  }],
]

function match(pattern: string, pathname: string): Record<string, string> | null {
  const want = pattern.split('/')
  const got = pathname.split('/')
  if (want.length !== got.length) return null
  const params: Record<string, string> = {}
  for (let i = 0; i < want.length; i += 1) {
    const segment = want[i]
    if (segment.startsWith(':')) {
      if (!got[i]) return null
      params[segment.slice(1)] = decodeURIComponent(got[i])
      continue
    }
    if (segment !== got[i]) return null
  }
  return params
}

export async function handleMock<T>(
  method: string,
  pathname: string,
  query: URLSearchParams,
  body: unknown,
  token: string | null,
): Promise<T> {
  await sleep(180 + Math.random() * 220)
  const user = userFromToken(token)
  const ctx: Ctx = {
    query,
    body: (body && typeof body === 'object' ? body : {}) as Record<string, unknown>,
    user,
  }
  for (const [verb, pattern, handler] of table) {
    if (verb !== method.toUpperCase()) continue
    const params = match(pattern, pathname)
    if (!params) continue
    const result = await handler(ctx, params)
    return result as T
  }
  throw new MockError(404, 'MOCK_ROUTE_MISSING', 'mock 没有实现 ' + method + ' ' + pathname)
}
