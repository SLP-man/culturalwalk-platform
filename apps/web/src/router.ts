import { createRouter, createWebHistory } from 'vue-router'

// 页面按目录一一对应 docs/00-总体开发文档.md §9 的 pages/ 列表
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'browse', component: () => import('@/pages/browse/index.vue') },
    {
      path: '/routes/:id',
      name: 'route-detail',
      component: () => import('@/pages/route-detail/index.vue'),
    },
    { path: '/planner', name: 'planner', component: () => import('@/pages/planner/index.vue') },
    { path: '/authoring', name: 'authoring', component: () => import('@/pages/authoring/index.vue') },
    { path: '/authoring/:id', name: 'authoring-edit', component: () => import('@/pages/authoring/index.vue') },
    { path: '/submit', name: 'submit', component: () => import('@/pages/submit/index.vue') },
    { path: '/me', name: 'me', component: () => import('@/pages/me/index.vue') },
    { path: '/login', name: 'login', component: () => import('@/pages/login/index.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/pages/admin/index.vue') },
  ],
})
