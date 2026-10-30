/**
 * 安全存储（shared/storage.ts）。
 *
 * 这个文件存在的原因：页面在模块顶层读 token / 用户信息，
 * 而 SSR 渲染与 Node 环境没有 localStorage。没有它，整站 import 就崩（nav.spec 曾因此红 8 条）。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { readItem, removeItem, writeItem } from '@/shared/storage'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('没有 localStorage 的环境（SSR / 测试）', () => {
  it('读写删走内存兜底，不抛异常', () => {
    expect(readItem('cw_token')).toBeNull()

    writeItem('cw_token', 'abc')
    expect(readItem('cw_token')).toBe('abc')

    removeItem('cw_token')
    expect(readItem('cw_token')).toBeNull()
  })
})

describe('有 localStorage 的环境（浏览器）', () => {
  it('写入落到 localStorage，读得到', () => {
    const store = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, value),
      removeItem: (key: string) => void store.delete(key),
    })

    writeItem('cw_user', '{"id":"u1"}')
    expect(store.get('cw_user')).toBe('{"id":"u1"}')
    expect(readItem('cw_user')).toBe('{"id":"u1"}')

    removeItem('cw_user')
    expect(store.has('cw_user')).toBe(false)
  })

  it('隐私模式下抛异常也不把页面带崩', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('SecurityError')
      },
      setItem: () => {
        throw new Error('QuotaExceededError')
      },
      removeItem: () => {
        throw new Error('SecurityError')
      },
    })

    expect(() => writeItem('cw_token', 'x')).not.toThrow()
    expect(readItem('cw_token')).toBe('x')
    expect(() => removeItem('cw_token')).not.toThrow()
  })
})
