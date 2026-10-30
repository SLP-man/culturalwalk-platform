import { describe, expect, it } from 'vitest'

import type { Schemas } from '@/api/types'

import {
  amapMarkerUrl,
  buildMapPins,
  confidenceTone,
  dayLabel,
  projectPoints,
  startTimeLabel,
} from '../logic'

type PlaceDetail = Schemas['PlaceDetail']
type RouteItem = NonNullable<NonNullable<Schemas['RouteDetail']['days']>[number]['items']>[number]

function place(partial: Partial<PlaceDetail>): PlaceDetail {
  return { id: 'p-1', name: '岳麓书院', lat: 28.1855, lon: 112.9513, ...partial }
}

function item(partial: Partial<RouteItem>): RouteItem {
  return { position: 1, stay_minutes: 60, transport: 'walk', ...partial }
}

describe('projectPoints', () => {
  it('把经纬度等比映射进 viewBox 且不越界', () => {
    const points = projectPoints([
      { lat: 28.1855, lon: 112.9513 },
      { lat: 28.1834, lon: 112.9442 },
    ])
    expect(points).toHaveLength(2)
    for (const point of points) {
      expect(point.x).toBeGreaterThanOrEqual(0)
      expect(point.x).toBeLessThanOrEqual(100)
      expect(point.y).toBeGreaterThanOrEqual(0)
      expect(point.y).toBeLessThanOrEqual(100)
    }
  })

  it('纬度大的点画在更靠上的位置（y 更小）', () => {
    const [north, south] = projectPoints([
      { lat: 28.2, lon: 112.95 },
      { lat: 28.1, lon: 112.95 },
    ])
    expect(north.y).toBeLessThan(south.y)
    expect(north.x).toBeCloseTo(south.x, 5)
  })

  it('单点与空列表都不会产出 NaN', () => {
    const [only] = projectPoints([{ lat: 28.1855, lon: 112.9513 }])
    expect(only).toEqual({ x: 50, y: 50 })
    expect(projectPoints([])).toEqual([])
  })
})

describe('amapMarkerUrl', () => {
  it('经纬度顺序是 lon,lat，并转义点位名', () => {
    expect(amapMarkerUrl('爱晚亭', 28.1834, 112.9442)).toBe(
      'https://uri.amap.com/marker?position=112.9442,28.1834&name=' + encodeURIComponent('爱晚亭'),
    )
    expect(amapMarkerUrl('A&B 店', 1, 2)).toBe(
      'https://uri.amap.com/marker?position=2,1&name=A%26B%20%E5%BA%97',
    )
  })
})

describe('buildMapPins', () => {
  it('保留时间线序号，跳过没有 place 的节点', () => {
    const pins = buildMapPins([
      item({ position: 1, place: place({ id: 'p-a', name: '岳麓书院' }) }),
      item({ position: 2, place: undefined }),
      item({ position: 3, place: place({ id: 'p-b', name: '爱晚亭', lat: 28.1834, lon: 112.9442 }) }),
    ])
    expect(pins.map((pin) => pin.index)).toEqual([1, 3])
    expect(pins.map((pin) => pin.name)).toEqual(['岳麓书院', '爱晚亭'])
  })

  it('没有坐标的节点全部跳过时返回空数组', () => {
    expect(buildMapPins([item({ place: undefined })])).toEqual([])
  })
})

describe('文案换算', () => {
  it('start_time 为空时显示「时间自定」', () => {
    expect(startTimeLabel(null)).toBe('时间自定')
    expect(startTimeLabel('  ')).toBe('时间自定')
    expect(startTimeLabel('09:30')).toBe('09:30')
  })

  it('可信度映射到三档颜色，未知值落到灰档', () => {
    expect(confidenceTone('verified')).toBe('ok')
    expect(confidenceTone('likely')).toBe('warn')
    expect(confidenceTone('unverified')).toBe('dim')
    expect(confidenceTone(undefined)).toBe('dim')
  })

  it('day_index 缺省按第 1 天算', () => {
    expect(dayLabel(2)).toBe('第 2 天')
    expect(dayLabel(undefined)).toBe('第 1 天')
  })
})
