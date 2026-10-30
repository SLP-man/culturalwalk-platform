/**
 * 请求层（shared/api.ts）的契约测试。
 *
 * 这里锁的是「所有页面共用的那一条通道」——最容易被改动、又最不容易被发现弄坏的地方：
 *   - token 要不要带、带在哪
 *   - 写操作有没有 Idempotency-Key（后端靠它防重复提交，漏了会造重复数据）
 *   - 改操作有没有 If-Match（漏了会覆盖别人的修改）
 *   - 后端错误信封有没有变成带 code 的 ApiError（页面按 code 分支，不按文案）
 */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

type ApiModule = typeof import('@/shared/api')

let api: ApiModule['api']
let ApiError: ApiModule['ApiError']
let setToken: ApiModule['setToken']

const fetchMock = vi.fn()

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeAll(async () => {
  // 走真请求分支：假数据开关关掉，再看 fetch 收到什么
  vi.stubEnv('VITE_USE_MOCK', 'false')
  vi.resetModules()
  const mod = await import('@/shared/api')
  api = mod.api
  ApiError = mod.ApiError
  setToken = mod.setToken
})

afterEach(() => {
  fetchMock.mockReset()
  setToken(null)
})

function installFetch(): void {
  vi.stubGlobal('fetch', fetchMock)
}

describe('共享请求层', () => {
  it('GET 不带 Authorization；setToken 之后每个请求都带上', async () => {
    installFetch()
    fetchMock.mockImplementation(async () => jsonResponse(200, { items: [] }))

    await api.get('/routes')
    let headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBeNull()

    setToken('token-abc')
    await api.get('/routes')
    headers = fetchMock.mock.calls[1][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer token-abc')
  })

  it('POST / DELETE 自动带 Idempotency-Key，GET 不带', async () => {
    installFetch()
    fetchMock.mockImplementation(async () => jsonResponse(201, { id: 'x' }))

    await api.post('/submissions', { title: '测试' })
    await api.get('/routes')
    const postHeaders = fetchMock.mock.calls[0][1].headers as Headers
    const getHeaders = fetchMock.mock.calls[1][1].headers as Headers

    expect(postHeaders.get('Idempotency-Key')).toMatch(/^[0-9a-f-]{36}$/)
    expect(getHeaders.get('Idempotency-Key')).toBeNull()
    // 两次写操作不能复用同一个 key，否则后端会把第二次当成重放吞掉
    await api.post('/submissions', { title: '测试' })
    const again = fetchMock.mock.calls[2][1].headers as Headers
    expect(again.get('Idempotency-Key')).not.toBe(postHeaders.get('Idempotency-Key'))
  })

  it('PATCH 把乐观锁版本放进 If-Match', async () => {
    installFetch()
    fetchMock.mockImplementation(async () => jsonResponse(200, { id: 'r1' }))

    await api.patch('/routes/r1', { title: '新标题' }, 7)
    const headers = fetchMock.mock.calls[0][1].headers as Headers

    expect(headers.get('If-Match')).toBe('7')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('204 返回 undefined，不把空响应当 JSON 解析', async () => {
    installFetch()
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))

    await expect(api.del('/routes/r1')).resolves.toBeUndefined()
  })

  it('后端错误信封被翻译成带 code 的 ApiError', async () => {
    installFetch()
    fetchMock.mockResolvedValue(
      jsonResponse(422, {
        error: {
          code: 'REVIEW_REASON_REQUIRED',
          message: '退回必须写理由',
          request_id: 'req-9',
        },
      }),
    )

    await expect(api.post('/review/tasks/t1/decide', {})).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      code: 'REVIEW_REASON_REQUIRED',
      requestId: 'req-9',
      message: '退回必须写理由',
    })
  })

  it('响应不是合法 JSON 时不崩，抛错里带状态码', async () => {
    installFetch()
    fetchMock.mockResolvedValue(new Response('<html>502</html>', { status: 502 }))

    const error = await api.get('/routes').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as InstanceType<ApiModule['ApiError']>).status).toBe(502)
  })
})
