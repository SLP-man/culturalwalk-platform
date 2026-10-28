/**
 * 底部导航的唯一配置处。
 *
 * 5 个主 tab 对应 docs/00-总体开发文档.md §9 的 pages/ 列表里可当一级入口的 5 个页面：
 * browse / planner / authoring / submit / me（route-detail、login、admin 不进主导航）。
 * 每个 tab 要能在 router 里点亮，靠的是对应路由上的 meta.nav。
 */

export type NavKey = 'browse' | 'planner' | 'authoring' | 'submit' | 'me'

export interface NavTab {
  key: NavKey
  to: string
  label: string
}

export const NAV_TABS: readonly NavTab[] = [
  { key: 'browse', to: '/', label: '发现' },
  { key: 'planner', to: '/planner', label: '规划' },
  { key: 'authoring', to: '/authoring', label: '创作' },
  { key: 'submit', to: '/submit', label: '投稿' },
  { key: 'me', to: '/me', label: '我的' },
]
