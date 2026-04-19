import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import AlertList from '@/views/AlertList.vue'
import AlertDetail from '@/views/AlertDetail.vue'
import Topology from '@/views/Topology.vue'
import Profile from '@/views/Profile.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard',
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/alerts',
    name: 'AlertList',
    component: AlertList,
    meta: { requiresAuth: true }
  },
  {
    path: '/alerts/:id',
    name: 'AlertDetail',
    component: AlertDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/topology',
    name: 'Topology',
    component: Topology,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false

  console.log(`[路由] ${from.path || '首次'} → ${to.path}`)

  if (requiresAuth && !token) {
    // 需要登录但未登录，跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else if (to.path === '/login' && token) {
    // 已登录访问登录页，跳转到仪表盘
    next('/dashboard')
  } else {
    next()
  }
})

export default router