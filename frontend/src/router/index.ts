import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Dashboard' }
  },
  {
    path: '/workers',
    name: 'Workers',
    component: () => import('@/views/WorkersView.vue'),
    meta: { title: 'Workers' }
  },
  {
    path: '/queue',
    name: 'Queue',
    component: () => import('@/views/QueueView.vue'),
    meta: { title: 'Job Queue' }
  },
  {
    path: '/scanner',
    name: 'Scanner',
    component: () => import('@/views/ScannerView.vue'),
    meta: { title: 'Library Scanner' }
  },
  {
    path: '/rules',
    name: 'Rules',
    component: () => import('@/views/RulesView.vue'),
    meta: { title: 'Scan Rules' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Settings' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'Transcriptarr'} - Transcriptarr`
  next()
})

export default router

