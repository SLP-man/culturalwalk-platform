/**
 * 登录页的纯函数部分：校验、错误文案、回跳地址。
 * 抽出来是为了能在 vitest 里直接测，不依赖 DOM 与 localStorage。
 */

export type AuthField = 'username' | 'password' | 'confirm'

export type AuthForm = {
  username: string
  password: string
  confirm?: string
}

export type FieldProblem = {
  field: AuthField
  message: string
}

export type DemoAccount = {
  username: string
  password: string
  /** 演示账号的角色说明，只用于按钮旁边的小字 */
  label: string
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: '文化漫步者', password: 'cw123456', label: '普通用户' },
  { username: '审核编辑', password: 'cw123456', label: '管理员' },
]

export const MIN_USERNAME_LENGTH = 2
export const MIN_PASSWORD_LENGTH = 6

/** 用户名前后空格不算字数，密码按原样算长度。 */
export function validateLogin(form: AuthForm): FieldProblem | null {
  if (form.username.trim().length < MIN_USERNAME_LENGTH) {
    return { field: 'username', message: `用户名至少 ${MIN_USERNAME_LENGTH} 个字` }
  }
  if (form.password.length < MIN_PASSWORD_LENGTH) {
    return { field: 'password', message: `密码至少 ${MIN_PASSWORD_LENGTH} 位` }
  }
  return null
}

export function validateRegister(form: AuthForm): FieldProblem | null {
  const base = validateLogin(form)
  if (base) return base
  if (form.password !== (form.confirm ?? '')) {
    return { field: 'confirm', message: '两次输入的密码不一致' }
  }
  return null
}

/** 契约里 code 稳定、message 只是给人看的，所以先按 code 映射，兜底才用 message。 */
const CODE_TEXT: Record<string, string> = {
  INVALID_CREDENTIALS: '用户名或密码不对',
  USERNAME_TAKEN: '这个用户名已经被用了',
}

export function authErrorText(code: string | null, message?: string): string {
  const mapped = code ? CODE_TEXT[code] : undefined
  if (mapped) return mapped
  const text = (message ?? '').trim()
  return text === '' ? '请求失败，请稍后重试' : text
}

/** 只认站内路径，避免 ?redirect= 被拿去做开放跳转。 */
export function redirectTarget(raw: unknown): string {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string') return '/'
  const path = value.trim()
  if (path === '' || !path.startsWith('/') || path.startsWith('//')) return '/'
  return path
}
