import type { RouteRecordRaw, RouterHistory } from 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'

import type { NavKey } from '@/shared/nav'

declare module 'vue-router' {
  interface RouteMeta {
    /** 这条路由点亮底部导航的哪个 tab；不设 = 不点亮任何 tab */
    nav?: NavKey
  }
}

// 页面按目录一一对应 docs/00-总体开发文档.md §9 的 pages/ 列表
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'browse',
    component: () => import('@/pages/browse/index.vue'),
    meta: { nav: 'browse' },
  },
  {
    path: '/routes/:id',
    name: 'route-detail',
    component: () => import('@/pages/route-detail/index.vue'),
    // 从列表点进来的详情页，底部导航仍然停在「发现」
    meta: { nav: 'browse' },
  },
  {
    path: '/planner',
    name: 'planner',
    component: () => import('@/pages/planner/index.vue'),
    meta: { nav: 'planner' },
  },
  {
    path: '/authoring',
    name: 'authoring',
    component: () => import('@/pages/authoring/index.vue'),
    meta: { nav: 'authoring' },
  },
  {
    path: '/authoring/:id',
    name: 'authoring-edit',
    component: () => import('@/pages/authoring/index.vue'),
    meta: { nav: 'authoring' },
  },
  {
    path: '/submit',
    name: 'submit',
    component: () => import('@/pages/submit/index.vue'),
    meta: { nav: 'submit' },
  },
  {
    path: '/me',
    name: 'me',
    component: () => import('@/pages/me/index.vue'),
    meta: { nav: 'me' },
  },
  // 登录页与后台不入主导航，所以不设 meta.nav
  { path: '/login', name: 'login', component: () => import('@/pages/login/index.vue') },
  { path: '/admin', name: 'admin', component: () => import('@/pages/admin/index.vue') },
  // 未知地址回首页：H5 上刷新错地址不该白屏
  { path: '/:pathMatch(.*)*', name: 'not-found', redirect: '/' },
]

/**
 * 路由器工厂：运行时用浏览器 history，测试传内存 history。
 * 这里不在模块顶层创建浏览器 history，否则在 Node 里 import 本文件（跑测试）会报 window is not defined。
 */
export function createAppRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes,
    scrollBehavior: () => ({ top: 0 }),
  })
}
