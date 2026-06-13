import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: () => import('@/views/AccountsList.vue'),
    meta: { title: '账号列表' },
  },
  {
    path: '/accounts/:id',
    name: 'account-detail',
    component: () => import('@/views/AccountDetail.vue'),
    meta: { title: '账号详情' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '设置' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} · TikTok Registrar`
})

export default router
