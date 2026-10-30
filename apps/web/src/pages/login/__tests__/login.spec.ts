import { describe, expect, it } from 'vitest'

import { authErrorText, redirectTarget, validateLogin, validateRegister } from '../validation'

describe('validateLogin', () => {
  it('用户名去空格后不足 2 字就拦下', () => {
    expect(validateLogin({ username: ' 甲 ', password: 'cw123456' })).toEqual({
      field: 'username',
      message: '用户名至少 2 个字',
    })
    expect(validateLogin({ username: '    ', password: 'cw123456' })?.field).toBe('username')
  })

  it('密码不足 6 位就拦下', () => {
    expect(validateLogin({ username: '甲先生', password: 'cw123' })).toEqual({
      field: 'password',
      message: '密码至少 6 位',
    })
  })

  it('合法输入返回 null', () => {
    expect(validateLogin({ username: '文化漫步者', password: 'cw123456' })).toBeNull()
  })
})

describe('validateRegister', () => {
  it('两次密码不一致时报在 confirm 上', () => {
    expect(validateRegister({ username: '甲先生', password: 'cw123456', confirm: 'cw12345' })).toEqual({
      field: 'confirm',
      message: '两次输入的密码不一致',
    })
  })

  it('确认密码留空也算不一致', () => {
    expect(
      validateRegister({ username: '甲先生', password: 'cw123456', confirm: '' })?.field,
    ).toBe('confirm')
  })

  it('先报用户名/密码问题，再报确认密码', () => {
    expect(
      validateRegister({ username: '甲', password: 'cw', confirm: 'cw123456' })?.field,
    ).toBe('username')
  })

  it('一致时通过', () => {
    expect(
      validateRegister({ username: '甲先生', password: 'cw123456', confirm: 'cw123456' }),
    ).toBeNull()
  })
})

describe('authErrorText', () => {
  it('按 code 映射后端错误', () => {
    expect(authErrorText('INVALID_CREDENTIALS', '随便什么文案')).toBe('用户名或密码不对')
    expect(authErrorText('USERNAME_TAKEN', '随便什么文案')).toBe('这个用户名已经被用了')
  })

  it('其他 code 用 error.message，包括 VALIDATION_FAILED', () => {
    expect(authErrorText('VALIDATION_FAILED', '用户名至少 2 个字')).toBe('用户名至少 2 个字')
    expect(authErrorText('SERVER_ERROR', '')).toBe('请求失败，请稍后重试')
  })
})

describe('redirectTarget', () => {
  it('缺省回首页，站内路径照用', () => {
    expect(redirectTarget(undefined)).toBe('/')
    expect(redirectTarget('/me')).toBe('/me')
    expect(redirectTarget(['/authoring/1'])).toBe('/authoring/1')
  })

  it('不把外层地址当回跳目标', () => {
    expect(redirectTarget('//evil.example.com')).toBe('/')
    expect(redirectTarget('https://evil.example.com')).toBe('/')
    expect(redirectTarget('')).toBe('/')
  })
})
