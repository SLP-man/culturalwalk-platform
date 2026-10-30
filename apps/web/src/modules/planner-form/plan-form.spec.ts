import { describe, expect, it } from 'vitest'

import {
  defaultForm,
  stepState,
  toPlanInput,
  toggleValue,
  validatePlanForm,
  type PlannerForm,
} from './plan-form'

function form(patch: Partial<PlannerForm> = {}): PlannerForm {
  return { ...defaultForm(), ...patch }
}

describe('validatePlanForm', () => {
  it('默认表单可以直接提交', () => {
    expect(validatePlanForm(defaultForm())).toBe('')
  })

  it('预算必须大于 0', () => {
    expect(validatePlanForm(form({ budgetYuan: 0 }))).toBe('总预算需要大于 0')
    expect(validatePlanForm(form({ budgetYuan: -1 }))).toBe('总预算需要大于 0')
  })

  it('天数限制 1-7 且必须是整数', () => {
    expect(validatePlanForm(form({ days: 0 }))).toBe('天数需要在 1-7 之间')
    expect(validatePlanForm(form({ days: 8 }))).toBe('天数需要在 1-7 之间')
    expect(validatePlanForm(form({ days: 2.5 }))).toBe('天数需要在 1-7 之间')
    expect(validatePlanForm(form({ days: 7 }))).toBe('')
  })

  it('人数限制 1-10 且必须是整数', () => {
    expect(validatePlanForm(form({ people: 0 }))).toBe('人数需要在 1-10 之间')
    expect(validatePlanForm(form({ people: 11 }))).toBe('人数需要在 1-10 之间')
    expect(validatePlanForm(form({ people: 10 }))).toBe('')
  })

  it('没选城市要拦住', () => {
    expect(validatePlanForm(form({ city: '' }))).toBe('请选择城市')
  })
})

describe('toPlanInput', () => {
  it('预算从元换成整数分', () => {
    expect(toPlanInput(form({ budgetYuan: 800 })).budget_total).toBe(80000)
    expect(toPlanInput(form({ budgetYuan: 88.8 })).budget_total).toBe(8880)
  })

  it('起点为空时不带 start_point，填了就写进 label', () => {
    expect(toPlanInput(form({ startPoint: '   ' })).start_point).toBeUndefined()
    expect(toPlanInput(form({ startPoint: '五一广场' })).start_point).toEqual({ label: '五一广场' })
  })

  it('多选项原样带上，且不改原表单数组', () => {
    const source = form({ themes: ['历史', '夜景'], transport: ['walk', 'metro'] })
    const input = toPlanInput(source)
    expect(input.themes).toEqual(['历史', '夜景'])
    expect(input.transport).toEqual(['walk', 'metro'])
    expect(input.day_parts).toEqual(['morning', 'afternoon', 'evening'])
    expect(input.pace).toBe('normal')
    input.themes?.push('江景')
    expect(source.themes).toEqual(['历史', '夜景'])
  })
})

describe('toggleValue', () => {
  it('没选就加上，选了就去掉', () => {
    expect(toggleValue(['上午'], '上午')).toEqual([])
    expect(toggleValue(['上午'], '下午')).toEqual(['上午', '下午'])
  })
})

describe('stepState', () => {
  it('只有已出现的最后一个在跑，前面的已完成，后面的未开始', () => {
    expect(stepState(0, 1)).toBe('running')
    expect(stepState(0, 2)).toBe('done')
    expect(stepState(1, 2)).toBe('running')
    expect(stepState(2, 2)).toBe('pending')
  })
})
