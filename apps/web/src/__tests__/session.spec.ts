/**
 * 登录态（shared/session.ts）的测试。
 *
 * 重点不是「登录成功」，而是「登录态坏掉的那几条路」：
 *   - 退出接口挂了，本地还能不能清干净（否则用户卡在假登录状态）
 *   - token 过期（401）之后，会不会把脏用户信息留在页面上
 */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

type SessionModule = typeof import('@/shared/session')
type ApiModule = typeof import('@/shared/api')

let session: SessionModule
let apiModule: ApiModule
let readItem: typeof import('@/shared/storage').readItem
const fetchMock = vi.fn()

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function tokenPair(username = 'xiaoming'): unknown {
  return {
    access_token: 'access-1',
    refresh_token: 'refresh-1',
    user: { id: 'u1', username, role: 'user' },
  }
}

beforeAll(async () => {
  vi.stubEnv('VITE_USE_MOCK', 'false')
  vi.resetModules()
  session = await import('@/shared/session')
  apiModule = await import('@/shared/api')
  readItem = (await import('@/shared/storage')).readItem
})

afterEach(() => {
  fetchMock.mockReset()
  apiModule.setToken(null)
})

describe('登录态', () => {
  it('登录成功后 token 与用户都落盘，isLoggedIn 变 true', async () => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValue(jsonResponse(200, tokenPair()))

    await session.login('xiaoming', 'cw123456')

    expect(readItem('cw_token')).toBe('access-1')
    expect(readItem('cw_refresh_token')).toBe('refresh-1')
    expect(session.isLoggedIn.value).toBe(true)
    expect(session.currentUser.value?.username).toBe('xiaoming')
  })

  it('普通用户不是管理员，isAdmin 为 false', async () => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValue(jsonResponse(200, tokenPair('normal')))

    await session.login('normal', 'cw123456')

    expect(session.isAdmin.value).toBe(false)
  })

  it('退出接口 500 也要把本地登录态清干净', async () => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValueOnce(jsonResponse(200, tokenPair()))
    await session.login('xiaoming', 'cw123456')

    fetchMock.mockResolvedValue(jsonResponse(500, { error: { code: 'BOOM', message: '炸了' } }))
    await session.logout()

    expect(readItem('cw_token')).toBeNull()
    expect(readItem('cw_refresh_token')).toBeNull()
    expect(readItem('cw_user')).toBeNull()
    expect(session.isLoggedIn.value).toBe(false)
  })

  it('token 过期（401）时 refreshMe 清空登录态而不是留个假用户', async () => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValueOnce(jsonResponse(200, tokenPair()))
    await session.login('xiaoming', 'cw123456')

    fetchMock.mockResolvedValue(jsonResponse(401, { error: { code: 'UNAUTHORIZED', message: '过期' } }))
    const me = await session.refreshMe()

    expect(me).toBeNull()
    expect(session.isLoggedIn.value).toBe(false)
    expect(readItem('cw_user')).toBeNull()
  })
})
