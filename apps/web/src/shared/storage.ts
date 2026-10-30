/**
 * localStorage 的安全封装。
 *
 * 为什么需要它：`shared/api.ts` 在模块顶层读 token，`shared/session.ts` 在模块顶层读用户。
 * 浏览器里没问题，但 SSR 渲染（`src/__tests__/nav.spec.ts` 用 `renderToString` 渲染真实页面）
 * 和 Node 环境里没有 `localStorage`，一 import 就 `ReferenceError`。
 *
 * 这里的规则：有 localStorage 就用它（浏览器），没有就退化成进程内 Map（测试/SSR）。
 * 页面和请求层一律走这里，不要直接摸 localStorage。
 */

const memory = new Map<string, string>()

function backing(): Storage | null {
  const candidate = (globalThis as { localStorage?: Storage }).localStorage
  return candidate ?? null
}

export function readItem(key: string): string | null {
  const ls = backing()
  if (ls) {
    try {
      return ls.getItem(key)
    } catch {
      // 隐私模式下 setItem/getItem 可能抛异常，退回内存
    }
  }
  return memory.get(key) ?? null
}

export function writeItem(key: string, value: string): void {
  const ls = backing()
  if (ls) {
    try {
      ls.setItem(key, value)
      return
    } catch {
      // 配额满或隐私模式：至少保证本次会话内可用
    }
  }
  memory.set(key, value)
}

export function removeItem(key: string): void {
  const ls = backing()
  if (ls) {
    try {
      ls.removeItem(key)
    } catch {
      /* 忽略：下面还会清内存副本 */
    }
  }
  memory.delete(key)
}
