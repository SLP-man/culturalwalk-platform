/**
 * 假数据 · 地点。FE-02~FE-09 先用它把页面跑起来，接口实现后关掉 mock 开关即可。
 *
 * 类型全部来自 @/api/types（契约生成），所以 openapi.yaml 改字段这里会立刻编译报错。
 * id 用可读字符串（如 p-yuelu）方便手改 URL 演示；真实接口返回 uuid。
 */

import type { Schemas } from '@/api/types'

type PlaceDetail = Schemas['PlaceDetail']

export const PLACES: PlaceDetail[] = [
  {
    id: 'p-yuelushuyuan',
    name: '岳麓书院',
    district: '岳麓区',
    lat: 28.1855,
    lon: 112.9513,
    summary: '北宋开宝九年创办，中国四大书院之一，讲堂与御书楼都在中轴线上。',
    culture_tags: ['书院', '历史', '建筑'],
    status: 'verified',
    open_hours: '07:30-18:00（17:30 停止入场）',
    open_hours_verified_at: '2026-04-12T02:00:00Z',
    facts: [
      {
        id: 'f-001',
        claim: '书院创建于北宋开宝九年（976 年），至今超过一千年。',
        confidence: 'verified',
        sources: [
          { title: '岳麓书院 · 书院沿革', url: 'https://example.org/yuelu-history', publisher: '岳麓书院' },
        ],
      },
      {
        id: 'f-002',
        claim: '讲堂内“忠孝廉节”四字为清代山长手书摹刻。',
        confidence: 'likely',
        sources: [{ title: '湖南地方志 · 教育卷', publisher: '湖南省地方志编委会' }],
      },
    ],
  },
  {
    id: 'p-aiwanting',
    name: '爱晚亭',
    district: '岳麓区',
    lat: 28.1834,
    lon: 112.9442,
    summary: '清乾隆年间所建，原名红叶亭，与醉翁亭、湖心亭、陶然亭并称四大名亭。',
    culture_tags: ['园林', '历史'],
    status: 'verified',
    facts: [
      {
        id: 'f-003',
        claim: '亭名取“停车坐爱枫林晚”，据传为清代湖广总督毕沅改题。',
        confidence: 'likely',
        sources: [{ title: '长沙名胜志', publisher: '长沙市文旅局' }],
      },
      {
        id: 'f-004',
        claim: '亭上匾额为毛泽东手书。',
        confidence: 'unverified',
        sources: [],
      },
    ],
  },
  {
    id: 'p-juzizhou',
    name: '橘子洲头',
    district: '岳麓区',
    lat: 28.1755,
    lon: 112.9616,
    summary: '湘江江心的长岛，青年毛泽东在此写下《沁园春 · 长沙》。',
    culture_tags: ['近代', '江景'],
    status: 'verified',
    open_hours: '07:00-22:00',
    open_hours_verified_at: '2026-03-20T02:00:00Z',
    facts: [
      {
        id: 'f-005',
        claim: '1925 年毛泽东重游橘子洲，写下《沁园春 · 长沙》。',
        confidence: 'verified',
        sources: [{ title: '毛泽东诗词全集', publisher: '人民文学出版社' }],
      },
    ],
  },
  {
    id: 'p-museum',
    name: '湖南博物院',
    district: '开福区',
    lat: 28.2146,
    lon: 112.9936,
    summary: '马王堆汉墓陈列在此，辛追夫人与素纱单衣是常设看点的核心。',
    culture_tags: ['博物馆', '考古'],
    status: 'verified',
    open_hours: '09:00-17:00（周一闭馆，需预约）',
    open_hours_verified_at: '2026-04-30T02:00:00Z',
    facts: [
      {
        id: 'f-006',
        claim: '素纱单衣总重 49 克，是已知最轻的汉代丝织品之一。',
        confidence: 'verified',
        sources: [{ title: '马王堆汉墓发掘报告', publisher: '文物出版社' }],
      },
    ],
  },
  {
    id: 'p-taiping',
    name: '太平老街',
    district: '天心区',
    lat: 28.1943,
    lon: 112.9739,
    summary: '清代街巷格局保留至今，街南端是贾谊故居。',
    culture_tags: ['街巷', '市井'],
    status: 'verified',
    facts: [
      {
        id: 'f-007',
        claim: '贾谊故居位于街南端，西汉贾谊任长沙王太傅时居于此。',
        confidence: 'verified',
        sources: [{ title: '长沙市文物局 · 贾谊故居', url: 'https://example.org/jiayi', publisher: '长沙市文物局' }],
      },
    ],
  },
  {
    id: 'p-chaozong',
    name: '潮宗街',
    district: '开福区',
    lat: 28.2058,
    lon: 112.9772,
    summary: '长沙保存较完整的老街区，麻石路面与近代公馆混杂。',
    culture_tags: ['街巷', '近代'],
    status: 'verified',
    facts: [
      {
        id: 'f-008',
        claim: '街上麻石路面为清代铺设，2010 年后按原样式修复。',
        confidence: 'likely',
        sources: [{ title: '开福区志', publisher: '开福区档案馆' }],
      },
    ],
  },
  {
    id: 'p-kaifusi',
    name: '开福寺',
    district: '开福区',
    lat: 28.2135,
    lon: 112.9788,
    summary: '五代后唐时期创建，佛殿与山门一线排开，香火延续至今。',
    culture_tags: ['宗教', '古建'],
    status: 'verified',
    open_hours: '08:00-17:30',
    open_hours_verified_at: null,
    facts: [
      {
        id: 'f-009',
        claim: '开福寺始建于后唐天成二年（927 年）。',
        confidence: 'verified',
        sources: [{ title: '开福寺 · 寺院简介', publisher: '开福寺' }],
      },
    ],
  },
  {
    id: 'p-tianxinge',
    name: '天心阁',
    district: '天心区',
    lat: 28.1872,
    lon: 112.9789,
    summary: '长沙古城墙仅存的一段，阁与城墙连成一体。',
    culture_tags: ['城墙', '历史'],
    status: 'verified',
    facts: [
      {
        id: 'f-010',
        claim: '现存城墙为明代长沙城墙遗存，长约 250 米。',
        confidence: 'likely',
        sources: [{ title: '长沙古城墙保护规划', publisher: '长沙市规划局' }],
      },
    ],
  },
  {
    id: 'p-baishajing',
    name: '白沙古井',
    district: '天心区',
    lat: 28.1878,
    lon: 112.9824,
    summary: '四眼古井并排，市民至今在此取水。',
    culture_tags: ['市井', '古迹'],
    status: 'verified',
    facts: [
      {
        id: 'f-011',
        claim: '白沙井水“煮茶不浊”，明清方志已有记载。',
        confidence: 'verified',
        sources: [{ title: '长沙府志', publisher: '湖南省图书馆' }],
      },
    ],
  },
  {
    id: 'p-diyishifan',
    name: '湖南第一师范',
    district: '天心区',
    lat: 28.1692,
    lon: 112.9762,
    summary: '原为南宋城南书院，近代改为师范学校，毛泽东曾在此求学任教。',
    culture_tags: ['近代', '教育'],
    status: 'verified',
    facts: [
      {
        id: 'f-012',
        claim: '校舍主体为 1912 年重建的仿日式建筑。',
        confidence: 'likely',
        sources: [{ title: '湖南第一师范校史', publisher: '第一师范' }],
      },
    ],
  },
]

export const PLACE_MAP: Record<string, PlaceDetail> = Object.fromEntries(
  PLACES.map((place) => [place.id, place]),
)

export interface DetailNode {
  placeId: string
  stayMinutes: number
  transport: 'walk' | 'metro' | 'bus' | 'taxi' | 'bike'
  priceMin?: number
  priceMax?: number
  startTime?: string
  note?: string
}

/** 三条有手写节点的路线；其余路线走 fallbackNodes()，保证任何 id 都能打开详情页。 */
export const ROUTE_NODES: Record<string, DetailNode[]> = {
  'r-yuelu': [
    { placeId: 'p-yuelushuyuan', stayMinutes: 90, transport: 'walk', priceMin: 4000, priceMax: 4000, startTime: '09:00', note: '先看讲堂与御书楼，二门内的碑刻别错过。' },
    { placeId: 'p-aiwanting', stayMinutes: 40, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '10:45' },
    { placeId: 'p-juzizhou', stayMinutes: 60, transport: 'metro', priceMin: 300, priceMax: 300, startTime: '13:30' },
  ],
  'r-laocheng': [
    { placeId: 'p-taiping', stayMinutes: 60, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '15:00' },
    { placeId: 'p-chaozong', stayMinutes: 45, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '16:20' },
    { placeId: 'p-kaifusi', stayMinutes: 40, transport: 'bus', priceMin: 200, priceMax: 200, startTime: '17:30' },
  ],
  'r-museum': [
    { placeId: 'p-museum', stayMinutes: 150, transport: 'metro', priceMin: 0, priceMax: 0, startTime: '09:30', note: '需提前在公众号预约，周一闭馆。' },
    { placeId: 'p-tianxinge', stayMinutes: 50, transport: 'taxi', priceMin: 1500, priceMax: 2000, startTime: '13:30' },
    { placeId: 'p-baishajing', stayMinutes: 25, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '15:00' },
  ],
}

export function fallbackNodes(): DetailNode[] {
  return [
    { placeId: 'p-taiping', stayMinutes: 60, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '10:00' },
    { placeId: 'p-baishajing', stayMinutes: 25, transport: 'walk', priceMin: 0, priceMax: 0, startTime: '11:20' },
  ]
}
