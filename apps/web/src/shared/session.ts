/**
 * 登录态。mock 模式下密码是 cw123456（见 shared/mock/workspace.ts），
 * 接口接好后这里一行都不用改：token 与 refresh_token 都由 /auth/login 返回。
 */

import { computed, reactive } from 'vue'

import type { Schemas } from '@/api/types'

import { api, setToken } from './api'

type User = Schemas['User']
type TokenPair = Schemas['TokenPair']

const USER_KEY = 'cw_user'
const REFRESH_KEY = 'cw_refresh_token'

function readUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

const state = reactive<{ user: User | null }>({ user: readUser() })

function persist(user: User | null): void {
  state.user = user
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

function adopt(pair: TokenPair): User {
  setToken(pair.access_token)
  localStorage.setItem(REFRESH_KEY, pair.refresh_token)
  persist(pair.user)
  return pair.user
}

export async function login(username: string, password: string): Promise<User> {
  return adopt(await api.post<TokenPair>('/auth/login', { username, password }))
}

export async function register(username: string, password: string): Promise<User> {
  return adopt(await api.post<TokenPair>('/auth/register', { username, password }))
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } catch {
    /* 后端不可达也要清掉本地登录态 */
  }
  setToken(null)
  localStorage.removeItem(REFRESH_KEY)
  persist(null)
}

/** 用 token 换最新用户信息；token 失效时清空登录态。 */
export async function refreshMe(): Promise<User | null> {
  if (!localStorage.getItem('cw_user')) return null
  try {
    const me = await api.get<User>('/users/me')
    persist(me)
    return me
  } catch {
    setToken(null)
    persist(null)
    return null
  }
}

export const currentUser = computed(() => state.user)
export const isLoggedIn = computed(() => state.user !== null)
export const isAdmin = computed(() => state.user?.role === 'admin')
