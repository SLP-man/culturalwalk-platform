/**
 * /me 页的展示规则。抽成纯函数，页面只负责拼装，规则单独可测。
 */

import type { Schemas } from '@/api/types'

import { durationLabel, moneyRange } from '@/shared/format'

type User = Schemas['User']
type UserProfile = Schemas['UserProfile']
type Notification = Schemas['Notification']
type RouteSummary = Schemas['RouteSummary']

export const EMPTY_BIO = '这个人还没有写简介'
export const EMPTY_ROUTES = '还没有发布过路线'
export const AVATAR_FALLBACK = '用'

const ROLE_LABEL: Record<User['role'], string> = {
  user: '普通用户',
  editor: '编辑',
  admin: '管理员',
}

const NOTICE_LABEL: Record<string, string> = {
  review_request_changes: '审核退回',
  review_approved: '审核通过',
  review_rejected: '审核未通过',
}

export function roleLabel(role: string | null | undefined): string {
  if (!role) return ROLE_LABEL.user
  return ROLE_LABEL[role as User['role']] ?? role
}

/** 头像占位取用户名首字；Array.from 才是按字素切，避免把代理对劈成半个字。 */
export function avatarInitial(username: string | null | undefined): string {
  const trimmed = (username ?? '').trim()
  if (!trimmed) return AVATAR_FALLBACK
  return Array.from(trimmed)[0]
}

export function bioText(bio: string | null | undefined): string {
  const trimmed = (bio ?? '').trim()
  return trimmed || EMPTY_BIO
}

/** 契约里 read_at 为空即未读。 */
export function isUnread(item: Pick<Notification, 'read_at'>): boolean {
  return !item.read_at
}

/** payload 是 unknown 字典，取出来要先确认是字符串才能直接渲染。 */
export function payloadText(payload: Notification['payload'], key: 'reason' | 'title'): string {
  const value = payload?.[key]
  return typeof value === 'string' ? value.trim() : ''
}

export function notificationKindLabel(type: string | null | undefined): string {
  if (!type) return '通知'
  return NOTICE_LABEL[type] ?? '通知'
}

export interface ProfileStats {
  published: number
  comments: number
}

export function profileStats(profile: UserProfile | null | undefined): ProfileStats {
  return {
    published: profile?.published_routes?.length ?? 0,
    comments: profile?.comment_count ?? 0,
  }
}

export interface RouteCardMeta {
  duration: string
  cost: string
  comments: number
  favorites: number
}

export function routeMeta(route: RouteSummary): RouteCardMeta {
  const cost = route.cost
  return {
    duration: durationLabel(route.duration_minutes),
    cost: moneyRange(cost?.min_total, cost?.max_total),
    comments: route.comment_count ?? 0,
    favorites: route.favorite_count ?? 0,
  }
}
