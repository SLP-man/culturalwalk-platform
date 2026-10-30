import { describe, expect, it } from 'vitest'

import type { Schemas } from '@/api/types'

import {
  AVATAR_FALLBACK,
  EMPTY_BIO,
  avatarInitial,
  bioText,
  isUnread,
  notificationKindLabel,
  payloadText,
  profileStats,
  roleLabel,
  routeMeta,
} from './logic'

function notice(readAt: string | null | undefined): Pick<Schemas['Notification'], 'read_at'> {
  return { read_at: readAt }
}

describe('/me 身份展示规则', () => {
  it('把三种角色翻成中文，未知角色原样显示', () => {
    expect(roleLabel('user')).toBe('普通用户')
    expect(roleLabel('editor')).toBe('编辑')
    expect(roleLabel('admin')).toBe('管理员')
    expect(roleLabel('guest')).toBe('guest')
    expect(roleLabel(null)).toBe('普通用户')
  })

  it('头像取首字，空名字给占位，代理对不劈开', () => {
    expect(avatarInitial('文化漫步者')).toBe('文')
    expect(avatarInitial('  ')).toBe(AVATAR_FALLBACK)
    expect(avatarInitial(undefined)).toBe(AVATAR_FALLBACK)
    expect(avatarInitial('🅰lex')).toBe('🅰')
  })

  it('简介为空时用兜底文案', () => {
    expect(bioText('在长沙住了七年')).toBe('在长沙住了七年')
    expect(bioText('   ')).toBe(EMPTY_BIO)
    expect(bioText(null)).toBe(EMPTY_BIO)
  })
})

describe('/me 通知规则', () => {
  it('read_at 为空即未读', () => {
    expect(isUnread(notice(null))).toBe(true)
    expect(isUnread(notice(undefined))).toBe(true)
    expect(isUnread(notice('2026-05-20T01:00:00Z'))).toBe(false)
  })

  it('payload 里只有字符串才算内容，其余当空', () => {
    expect(payloadText({ reason: ' 请补充营业时间 ' }, 'reason')).toBe('请补充营业时间')
    expect(payloadText({ title: '湘江边的傍晚散步' }, 'title')).toBe('湘江边的傍晚散步')
    expect(payloadText({}, 'reason')).toBe('')
    expect(payloadText(undefined, 'reason')).toBe('')
    expect(payloadText({ reason: null }, 'reason')).toBe('')
    expect(payloadText({ reason: 42 }, 'reason')).toBe('')
  })

  it('通知类型翻成中文，未知类型退回通用标题', () => {
    expect(notificationKindLabel('review_request_changes')).toBe('审核退回')
    expect(notificationKindLabel('review_approved')).toBe('审核通过')
    expect(notificationKindLabel('system_broadcast')).toBe('通知')
    expect(notificationKindLabel(null)).toBe('通知')
  })
})

describe('/me 统计与路线卡片', () => {
  it('统计行取已发布路线数与评论数，缺字段算 0', () => {
    const profile = {
      user: { id: 'u-001', username: '文化漫步者', role: 'user' as const },
      published_routes: [{ id: 'r-1', title: '甲', channel: 'user' as const }],
      comment_count: 2,
    }
    expect(profileStats(profile)).toEqual({ published: 1, comments: 2 })
    expect(
      profileStats({
        user: { id: 'u-2', username: '乙', role: 'user' as const },
        published_routes: [],
      }),
    ).toEqual({ published: 0, comments: 0 })
    expect(profileStats(null)).toEqual({ published: 0, comments: 0 })
  })

  it('路线卡片用时长/价格区间（分→元）与评论收藏数', () => {
    const meta = routeMeta({
      id: 'r-2',
      title: '两日亲子：书院与江滩',
      channel: 'user',
      duration_minutes: 150,
      cost: { min_total: 3000, max_total: 5000, currency: 'CNY' },
      comment_count: 4,
      favorite_count: 9,
    })
    expect(meta).toEqual({ duration: '2 小时 30 分', cost: '¥30-¥50', comments: 4, favorites: 9 })
  })

  it('缺少时长与价格时给待定文案', () => {
    const meta = routeMeta({ id: 'r-3', title: '无价路线', channel: 'official' })
    expect(meta).toEqual({ duration: '时长待定', cost: '价格待核实', comments: 0, favorites: 0 })
  })
})
