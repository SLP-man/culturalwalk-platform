/**
 * 统一请求封装。页面里不要直接 fetch。
 *
 * 约定（见 docs/03-接口契约规范.md）：
 * - 前缀 /api/v1，由 vite 代理到后端
 * - 写操作自动带 Idempotency-Key
 * - 非 2xx 抛 ApiError，页面按 code 分支而不是 message 文案
 */

import { MockError, handleMock } from './mock/handlers'
import { readItem, removeItem, writeItem } from './storage'

export interface ApiErrorBody {
  error: { code: string; message: string; request_id?: string; details?: unknown[] }
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const BASE = '/api/v1'

/**
 * 假数据开关。开发环境默认开，接口就绪后设 VITE_USE_MOCK=false 即可走真接口。
 * 页面永远只调 api.get/post/patch/del，不要自己判断 USE_MOCK。
 */
const mockFlag = import.meta.env.VITE_USE_MOCK
export const USE_MOCK =
  mockFlag === 'true' ? true : mockFlag === 'false' ? false : import.meta.env.DEV

function uuid(): string {
  return crypto.randomUUID()
}

let accessToken: string | null = readItem('cw_token')
export function setToken(token: string | null): void {
  accessToken = token
  if (token) writeItem('cw_token', token)
  else removeItem('cw_token')
}

export async function request<T>(
  path: string,
  init: RequestInit & { idempotent?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const isWrite = (init.method ?? 'GET').toUpperCase() !== 'GET'
  if (init.idempotent ?? isWrite) {
    headers.set('Idempotency-Key', uuid())
  }

  const method = (init.method ?? 'GET').toUpperCase()
  if (USE_MOCK) {
    const [pathname, search] = path.split('?')
    const query = new URLSearchParams(search ?? '')
    const body = init.body ? JSON.parse(String(init.body)) : undefined
    try {
      return await handleMock<T>(method, pathname, query, body, accessToken)
    } catch (error) {
      if (error instanceof MockError) {
        throw new ApiError(error.status, error.code, error.message)
      }
      throw error
    }
  }

  const res = await fetch(BASE + path, { ...init, headers })

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      // 网关/nginx 出错时返回的是 HTML，不能让页面崩在 JSON.parse 上
      throw new ApiError(
        res.status,
        'BAD_RESPONSE',
        res.ok ? '响应格式不是 JSON' : `请求失败（${res.status}）`,
      )
    }
  }

  if (!res.ok) {
    const err = data as ApiErrorBody | null
    throw new ApiError(
      res.status,
      err?.error.code ?? 'UNKNOWN',
      err?.error.message ?? `请求失败（${res.status}）`,
      err?.error.request_id,
    )
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown, lockVersion: number) =>
    request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
      headers: { 'If-Match': String(lockVersion) },
    }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
