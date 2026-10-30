/**
 * 路线详情页的纯逻辑：从组件里抽出来，才能直接跑 vitest。
 * 只做展示层换算，不发请求。
 */

import type { Schemas } from '@/api/types'

type RouteDetail = Schemas['RouteDetail']
export type RouteItem = NonNullable<NonNullable<RouteDetail['days']>[number]['items']>[number]

export interface MapPin {
  /** 与时间线一致的序号，从 1 开始 */
  index: number
  name: string
  x: number
  y: number
}

const DEFAULT_VIEW = 100
const DEFAULT_PAD = 12

function round(value: number): number {
  return Math.round(value * 100) / 100
}

/**
 * 经纬度 → viewBox 坐标。用等比缩放，避免长沙这种几公里的范围被拉成方块。
 * 单点、全部重合或空列表都不做除法，直接居中/返回空。
 */
export function projectPoints(
  coords: { lat: number; lon: number }[],
  view: number = DEFAULT_VIEW,
  pad: number = DEFAULT_PAD,
): { x: number; y: number }[] {
  if (coords.length === 0) return []
  const center = view / 2
  const inner = Math.max(view - pad * 2, 1)
  const lats = coords.map((coord) => coord.lat)
  const lons = coords.map((coord) => coord.lon)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const span = Math.max(maxLat - minLat, maxLon - minLon)
  if (!span) return coords.map(() => ({ x: round(center), y: round(center) }))

  const scale = inner / span
  const midLat = (minLat + maxLat) / 2
  const midLon = (minLon + maxLon) / 2
  return coords.map((coord) => ({
    x: round(center + (coord.lon - midLon) * scale),
    // 纬度越大越靠北，屏幕 y 轴向下，所以取反
    y: round(center - (coord.lat - midLat) * scale),
  }))
}

/** 高德 uri 的经纬度顺序是 lon,lat，别写反了。 */
export function amapMarkerUrl(name: string, lat: number, lon: number): string {
  return 'https://uri.amap.com/marker?position=' + lon + ',' + lat + '&name=' + encodeURIComponent(name)
}

/** 时间线序号 + 坐标；没有 place 的节点跳过，但序号仍按原位置算。 */
export function buildMapPins(items: RouteItem[]): MapPin[] {
  const usable: { index: number; place: Schemas['PlaceDetail'] }[] = []
  items.forEach((item, offset) => {
    if (item.place) usable.push({ index: item.position ?? offset + 1, place: item.place })
  })
  const coords = projectPoints(usable.map((entry) => ({ lat: entry.place.lat, lon: entry.place.lon })))
  return usable.map((entry, i) => ({
    index: entry.index,
    name: entry.place.name,
    x: coords[i].x,
    y: coords[i].y,
  }))
}

export function startTimeLabel(value: string | null | undefined): string {
  const text = (value ?? '').trim()
  return text || '时间自定'
}

export function dayLabel(dayIndex: number | undefined): string {
  return '第 ' + (dayIndex ?? 1) + ' 天'
}

/** 可信度 → 徽标色档，样式在页面的 <style scoped> 里。 */
export function confidenceTone(value: string | null | undefined): 'ok' | 'warn' | 'dim' {
  if (value === 'verified') return 'ok'
  if (value === 'likely') return 'warn'
  return 'dim'
}
