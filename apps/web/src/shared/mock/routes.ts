/**
 * 假数据 · 路线与评论。10 条路线与 docs/05-演示脚本与验收.md 里“演示数据”的量级一致。
 */

import type { Schemas } from '@/api/types'

import { PLACE_MAP, ROUTE_NODES, fallbackNodes } from './places'

type RouteSummary = Schemas['RouteSummary']
type RouteDetail = Schemas['RouteDetail']
type Comment = Schemas['Comment']

export const ROUTES: RouteSummary[] = [
  {
    id: 'r-yuelu',
    title: '岳麓山下的千年书声',
    summary: '从岳麓书院走到爱晚亭，再下山看湘江北去。半天步行为主，适合第一次来长沙的人。',
    cover_url: null,
    channel: 'official',
    author: { id: 'u-900', username: '平台编辑部' },
    theme_tags: ['历史', '书院', '山水'],
    duration_minutes: 240,
    cost: { min_total: 4300, max_total: 4300, currency: 'CNY', unknown_count: 0 },
    comment_count: 3,
    favorite_count: 42,
  },
  {
    id: 'r-laocheng',
    title: '老街巷里的长沙',
    summary: '太平街、潮宗街、开福寺一条线，看麻石路与近代公馆怎么长在一起。',
    cover_url: null,
    channel: 'official',
    author: { id: 'u-900', username: '平台编辑部' },
    theme_tags: ['街巷', '市井'],
    duration_minutes: 180,
    cost: { min_total: 200, max_total: 200, currency: 'CNY', unknown_count: 0 },
    comment_count: 1,
    favorite_count: 28,
  },
  {
    id: 'r-museum',
    title: '博物院与古城墙的一天',
    summary: '上午马王堆，下午天心阁城墙与白沙井，室内室外各半，雨天也能走。',
    cover_url: null,
    channel: 'official',
    author: { id: 'u-900', username: '平台编辑部' },
    theme_tags: ['博物馆', '历史'],
    duration_minutes: 300,
    cost: { min_total: 1500, max_total: 2000, currency: 'CNY', unknown_count: 0 },
    comment_count: 0,
    favorite_count: 17,
  },
  {
    id: 'r-jiangbian',
    title: '湘江边的傍晚散步',
    summary: '橘子洲头看日落，再沿江走一段，两小时不到。',
    cover_url: null,
    channel: 'user',
    author: { id: 'u-001', username: '文化漫步者' },
    theme_tags: ['江景', '散步'],
    duration_minutes: 110,
    cost: { min_total: 300, max_total: 600, currency: 'CNY', unknown_count: 1 },
    comment_count: 2,
    favorite_count: 9,
  },
  {
    id: 'r-shifan',
    title: '第一师范到白沙井',
    summary: '一条以近代教育史为主线的城南步行路线，全程约 2.5 公里。',
    cover_url: null,
    channel: 'user',
    author: { id: 'u-001', username: '文化漫步者' },
    theme_tags: ['近代', '教育'],
    duration_minutes: 150,
    cost: { min_total: 0, max_total: 0, currency: 'CNY', unknown_count: 0 },
    comment_count: 0,
    favorite_count: 5,
  },
  {
    id: 'r-kaifu',
    title: '开福寺半日静走',
    summary: '寺院、斋饭与周边老巷，节奏放慢一点。',
    cover_url: null,
    channel: 'user',
    author: { id: 'u-001', username: '文化漫步者' },
    theme_tags: ['宗教', '古建'],
    duration_minutes: 120,
    cost: { min_total: 1000, max_total: 1500, currency: 'CNY', unknown_count: 0 },
    comment_count: 1,
    favorite_count: 12,
  },
  {
    id: 'r-tianxin',
    title: '天心阁城墙上的长沙',
    summary: '一段 250 米的明城墙，讲清长沙城为什么长成这样。',
    cover_url: null,
    channel: 'official',
    author: { id: 'u-900', username: '平台编辑部' },
    theme_tags: ['城墙', '历史'],
    duration_minutes: 90,
    cost: { min_total: 3200, max_total: 3200, currency: 'CNY', unknown_count: 0 },
    comment_count: 0,
    favorite_count: 21,
  },
  {
    id: 'r-qinzi',
    title: '亲子半日：书院与江滩',
    summary: '给 6-10 岁孩子准备的短路线，中间有两次休息和一次江滩玩水。',
    cover_url: null,
    channel: 'user',
    author: { id: 'u-001', username: '文化漫步者' },
    theme_tags: ['亲子', '散步'],
    duration_minutes: 150,
    cost: { min_total: 4000, max_total: 6000, currency: 'CNY', unknown_count: 1 },
    comment_count: 0,
    favorite_count: 7,
  },
  {
    id: 'r-yexiao',
    title: '夜里两小时的市井线',
    summary: '晚上的太平街与坡子街，重点是摊子和灯，不是店。',
    cover_url: null,
    channel: 'user',
    author: { id: 'u-001', username: '文化漫步者' },
    theme_tags: ['市井', '夜景'],
    duration_minutes: 120,
    cost: { min_total: 2000, max_total: 5000, currency: 'CNY', unknown_count: 2 },
    comment_count: 0,
    favorite_count: 15,
  },
  {
    id: 'r-shuyuan2',
    title: '两座书院对照走读',
    summary: '岳麓书院与城南书院（第一师范前身）对照着看，一天走完。',
    cover_url: null,
    channel: 'official',
    author: { id: 'u-900', username: '平台编辑部' },
    theme_tags: ['书院', '教育', '历史'],
    duration_minutes: 330,
    cost: { min_total: 4300, max_total: 4800, currency: 'CNY', unknown_count: 0 },
    comment_count: 0,
    favorite_count: 11,
  },
]

export const ROUTE_MAP: Record<string, RouteSummary> = Object.fromEntries(
  ROUTES.map((route) => [route.id, route]),
)

export function buildRouteDetail(id: string): RouteDetail | null {
  const summary = ROUTE_MAP[id]
  if (!summary) return null
  const nodes = ROUTE_NODES[id] ?? fallbackNodes()
  return {
    ...summary,
    version_id: 'v-' + id + '-3',
    content_hash: 'sha256:mock-' + id,
    published_at: '2026-05-18T02:00:00Z',
    is_favorited: false,
    days: [
      {
        day_index: 1,
        items: nodes.map((node, index) => {
          const place = PLACE_MAP[node.placeId]
          const confidence: 'verified' | 'likely' | 'unverified' = place?.facts?.some(
            (fact) => fact.confidence === 'verified',
          )
            ? 'verified'
            : place?.facts?.length
              ? 'likely'
              : 'unverified'
          return {
            position: index + 1,
            start_time: node.startTime ?? null,
            stay_minutes: node.stayMinutes,
            transport: node.transport,
            place,
            price_min: node.priceMin ?? null,
            price_max: node.priceMax ?? null,
            confidence,
          }
        }),
      },
    ],
  }
}

export const COMMENTS: Comment[] = [
  {
    id: 'c-001',
    route_id: 'r-yuelu',
    body: '爱晚亭那段石阶在雨后很滑，带孩子的话建议走大路。',
    pinned: true,
    author: { id: 'u-001', username: '文化漫步者' },
    created_at: '2026-05-20T06:20:00Z',
  },
  {
    id: 'c-002',
    route_id: 'r-yuelu',
    body: '书院门票 40 元，学生半价，记得带证件。',
    pinned: false,
    author: { id: 'u-002', username: '橘子洲头看日出' },
    created_at: '2026-05-19T11:02:00Z',
  },
  {
    id: 'c-003',
    route_id: 'r-yuelu',
    body: '周一人少，讲解基本能凑上。',
    pinned: false,
    author: { id: 'u-003', username: '湘江散步' },
    created_at: '2026-05-15T03:40:00Z',
  },
]

/** 筛选条用的主题与时长选项（时长 value 与契约 ?duration=0-120 的写法一致） */
export const THEME_OPTIONS = [
  '历史',
  '书院',
  '街巷',
  '市井',
  '博物馆',
  '江景',
  '亲子',
  '近代',
  '宗教',
  '城墙',
  '山水',
  '教育',
  '古建',
  '散步',
  '夜景',
]

export const DURATION_OPTIONS = [
  { label: '2 小时以内', value: '0-120' },
  { label: '2-4 小时', value: '120-240' },
  { label: '4 小时以上', value: '240-' },
]
