<template>
  <el-container class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>OPS Platform</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard" @click="navigateTo('/dashboard')">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/alerts" @click="navigateTo('/alerts')">
          <el-icon><Bell /></el-icon>
          <span>告警管理</span>
        </el-menu-item>
        <el-menu-item index="/topology" @click="navigateTo('/topology')">
          <el-icon><Share /></el-icon>
          <span>服务拓扑</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute">{{ currentRoute }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-badge :value="pendingAlerts" :hidden="pendingAlerts === 0">
            <el-icon :size="20"><Bell /></el-icon>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="30" :src="fullAvatarUrl" style="margin-right: 8px">
                <el-icon><User /></el-icon>
              </el-avatar>
              {{ userName }} <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main>
        <router-view :key="$route.fullPath" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataLine, Bell, Share, User, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { getDashboardOverview } from '@/api'
import { logout } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const activeMenu = ref('/dashboard')
const pendingAlerts = ref(0)

const userName = ref('Admin')
const userAvatar = ref('')

// 计算完整的头像 URL
const fullAvatarUrl = computed(() => {
  const avatar = userAvatar.value
  if (!avatar) return ''
  // 如果是完整的 URL 或 Base64，直接返回
  if (avatar.startsWith('http') || avatar.startsWith('data:image')) {
    return avatar
  }
  // 如果是相对路径，加上后端地址
  if (avatar.startsWith('/')) {
    return `http://localhost:5000${avatar}`
  }
  return avatar
})

const currentRoute = computed(() => {
  const path = route.path
  if (path === '/dashboard') return '仪表盘'
  if (path === '/alerts') return '告警管理'
  if (path.startsWith('/alerts/')) return '告警详情'
  if (path === '/topology') return '服务拓扑'
  if (path === '/profile') return '个人设置'
  return ''
})

const navigateTo = (path) => {
  console.log('Navigating to:', path)
  activeMenu.value = path
  router.push(path).catch(err => {
    console.error('Navigation error:', err)
    window.location.href = path
  })
}

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    handleLogout()
  }
}

const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
    console.error('Logout error:', error)
  } finally {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

// 加载用户信息
const loadUserInfo = () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      const user = JSON.parse(userStr)
      userName.value = user.name || user.username || 'Admin'
      userAvatar.value = user.avatar || ''
      console.log('Loaded user info:', { name: userName.value, avatar: userAvatar.value })
    } catch (e) {
      console.error('Failed to parse user info:', e)
    }
  }
}

// 监听路由变化，刷新用户信息（从个人设置返回时更新）
watch(
  () => route.path,
  () => {
    loadUserInfo()
  }
)

watch(
  () => route.path,
  (newPath) => {
    if (newPath.startsWith('/alerts')) {
      activeMenu.value = '/alerts'
    } else if (newPath === '/topology') {
      activeMenu.value = '/topology'
    } else if (newPath === '/dashboard') {
      activeMenu.value = '/dashboard'
    } else if (newPath === '/profile') {
      activeMenu.value = ''
    }
  },
  { immediate: true }
)

const fetchPendingAlerts = async () => {
  try {
    const res = await getDashboardOverview()
    pendingAlerts.value = res.summary?.pending_alerts || 0
  } catch (error) {
    console.error('Failed to fetch alerts count:', error)
  }
}

onMounted(() => {
  loadUserInfo()
  fetchPendingAlerts()
  setInterval(fetchPendingAlerts, 30000)
})

// 使用 onActivated 确保组件激活时刷新（配合 keep-alive 使用）
onActivated(() => {
  loadUserInfo()
})
</script>

<style scoped>
/* 保持原有样式 */
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #4a5a6a;
}

.logo h2 {
  font-size: 18px;
  margin: 0;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.el-menu {
  border-right: none;
}
</style>