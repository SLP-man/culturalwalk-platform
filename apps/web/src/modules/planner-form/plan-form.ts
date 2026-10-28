/**
 * 规划表单的纯逻辑：默认值、选项、校验、PlanInput 组装。
 * 表单组件只负责渲染，页面只负责发请求，规则全在这里以便单测。
 */

import type { PlanInput } from '@/api/types'
import { transportLabel } from '@/shared/format'

export type PlanDayPart = NonNullable<PlanInput['day_parts']>[number]
export type PlanTransport = NonNullable<PlanInput['transport']>[number]
export type PlanPace = NonNullable<PlanInput['pace']>

/** 表单态：金额用「元」填写，提交时才换成「分」 */
export interface PlannerForm {
  city: string
  days: number
  people: number
  budgetYuan: number
  includeLodging: boolean
  dayParts: PlanDayPart[]
  themes: string[]
  transport: PlanTransport[]
  pace: PlanPace
  startPoint: string
}

export const DAYS_MIN = 1
export const DAYS_MAX = 7
export const PEOPLE_MIN = 1
export const PEOPLE_MAX = 10

export const CITY_OPTIONS: { value: string; label: string }[] = [
  { value: 'changsha', label: '长沙' },
]

export const DAY_PART_OPTIONS: { value: PlanDayPart; label: string }[] = [
  { value: 'morning', label: '上午' },
  { value: 'afternoon', label: '下午' },
  { value: 'evening', label: '晚上' },
]

export const THEME_OPTIONS: string[] = [
  '历史',
  '书院',
  '街巷',
  '市井',
  '博物馆',
  '江景',
  '亲子',
  '夜景',
]

export const TRANSPORT_OPTIONS: { value: PlanTransport; label: string }[] = (
  ['walk', 'metro', 'bus', 'taxi', 'bike'] as PlanTransport[]
).map((value) => ({ value, label: transportLabel(value) }))

export const PACE_OPTIONS: { value: PlanPace; label: string }[] = [
  { value: 'relaxed', label: '轻松' },
  { value: 'normal', label: '适中' },
  { value: 'packed', label: '紧凑' },
]

export function defaultForm(): PlannerForm {
  return {
    city: 'changsha',
    days: 2,
    people: 2,
    budgetYuan: 800,
    includeLodging: false,
    // 时段默认全选，用户再按需去掉
    dayParts: ['morning', 'afternoon', 'evening'],
    themes: [],
    transport: ['walk', 'metro'],
    pace: 'normal',
    startPoint: '',
  }
}

/** 多选 chip 的增删；返回新数组，避免原地改 props */
export function toggleValue<T>(list: readonly T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}

/** 返回第一条错误文案，空串表示可以提交 */
export function validatePlanForm(form: PlannerForm): string {
  if (!form.city) return '请选择城市'
  if (!Number.isInteger(form.days) || form.days < DAYS_MIN || form.days > DAYS_MAX) {
    return `天数需要在 ${DAYS_MIN}-${DAYS_MAX} 之间`
  }
  if (!Number.isInteger(form.people) || form.people < PEOPLE_MIN || form.people > PEOPLE_MAX) {
    return `人数需要在 ${PEOPLE_MIN}-${PEOPLE_MAX} 之间`
  }
  if (!Number.isFinite(form.budgetYuan) || form.budgetYuan <= 0) return '总预算需要大于 0'
  return ''
}

/** 元 → 分；start_point 为空时不提交，避免后端存一个空标签 */
export function toPlanInput(form: PlannerForm): PlanInput {
  const input: PlanInput = {
    city: form.city,
    days: form.days,
    people: form.people,
    budget_total: Math.round(form.budgetYuan * 100),
    include_lodging: form.includeLodging,
    day_parts: [...form.dayParts],
    themes: [...form.themes],
    transport: [...form.transport],
    pace: form.pace,
  }
  const label = form.startPoint.trim()
  if (label) input.start_point = { label }
  return input
}

export type StepState = 'done' | 'running' | 'pending'

/** 第 index 个步骤在「已出现 revealed 个」时的状态 */
export function stepState(index: number, revealed: number): StepState {
  if (index < 0 || index >= revealed) return 'pending'
  return index === revealed - 1 ? 'running' : 'done'
}
