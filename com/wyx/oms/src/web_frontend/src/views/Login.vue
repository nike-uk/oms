<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>OPS Platform</h1>
        <p>运维数据分析与管理系统</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="loginForm.remember">记住密码</el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            登 录
          </el-button>
        </el-form-item>

        <div class="login-tip">
          <span>演示账号: admin / admin123</span>
          <span>普通用户: user / user123</span>
        </div>
      </el-form>
    </div>

    <div class="login-footer">
      <span>© 2026 OPS Platform. All rights reserved.</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '@/api/auth'

const router = useRouter()
const route = useRoute()

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 检查本地存储中是否有保存的账号
const savedUsername = localStorage.getItem('savedUsername')
const savedPassword = localStorage.getItem('savedPassword')
if (savedUsername && savedPassword) {
  loginForm.username = savedUsername
  loginForm.password = savedPassword
  loginForm.remember = true
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await login({
        username: loginForm.username,
        password: loginForm.password
      })

      // 保存 token
      localStorage.setItem('token', res.token)
      localStorage.setItem('user', JSON.stringify(res.user))

      // 记住密码
      if (loginForm.remember) {
        localStorage.setItem('savedUsername', loginForm.username)
        localStorage.setItem('savedPassword', loginForm.password)
      } else {
        localStorage.removeItem('savedUsername')
        localStorage.removeItem('savedPassword')
      }

      ElMessage.success('登录成功')

      // 跳转到之前的页面或仪表盘
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
    } catch (error) {
      ElMessage.error(error.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 10px;
}

.login-header p {
  font-size: 14px;
  color: #909399;
}

.login-form {
  margin-top: 20px;
}

.login-btn {
  width: 100%;
}

.login-tip {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.login-footer {
  position: fixed;
  bottom: 20px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}
</style>