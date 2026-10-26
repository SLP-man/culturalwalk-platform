/**
 * 契约类型入口。页面/组件只从这里 import 类型，不要直接写 interface。
 *
 * 由 docs/api/openapi.yaml 生成：
 *   在 apps/web 下执行 pnpm gen
 *
 * 用法：
 *   import type { Schemas } from '@/api/types'
 *   const route: Schemas['RouteDetail'] = ...
 */
export type { paths, components, operations } from '@cw/contracts'

import type { components } from '@cw/contracts'

/** 所有 schema 的短别名，写起来更省事 */
export type Schemas = components['schemas']

/** 常用别名（契约里改了名字，这里会立刻报错，正好提醒改代码） */
export type RouteSummary = Schemas['RouteSummary']
export type RouteDetail = Schemas['RouteDetail']
export type RouteDraftDetail = Schemas['RouteDraftDetail']
export type PlanInput = Schemas['PlanInput']
export type PlanDetail = Schemas['PlanDetail']
export type Error = Schemas['Error']
