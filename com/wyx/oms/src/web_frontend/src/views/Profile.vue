<template>
  <div class="profile-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span><el-icon><User /></el-icon> 个人设置</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="card">
        <!-- 基本资料 -->
        <el-tab-pane label="基本资料" name="basic">
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="100px"
            style="max-width: 500px"
          >
            <el-form-item label="头像">
              <el-upload
                class="avatar-uploader"
                action="#"
                :show-file-list="false"
                :before-upload="handleAvatarUpload"
              >
                <el-avatar :size="80" :src="profileForm.avatar">
                  <el-icon :size="40"><User /></el-icon>
                </el-avatar>
                <el-button link type="primary" style="margin-left: 15px">
                  更换头像
                </el-button>
              </el-upload>
            </el-form-item>

            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" disabled />
            </el-form-item>

            <el-form-item label="姓名" prop="name">
              <el-input v-model="profileForm.name" placeholder="请输入姓名" />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
            </el-form-item>

            <el-form-item label="手机号" prop="phone">
              <el-input v-model="profileForm.phone" placeholder="请输入手机号" />
            </el-form-item>

            <el-form-item label="角色">
              <el-tag :type="profileForm.role === 'admin' ? 'danger' : 'info'">
                {{ profileForm.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveProfile">
                保存修改
              </el-button>
              <el-button @click="resetProfile">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 修改密码 -->
        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            style="max-width: 400px"
          >
            <el-form-item label="原密码" prop="oldPassword">
              <el-input
                v-model="passwordForm.oldPassword"
                type="password"
                placeholder="请输入原密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                placeholder="请输入新密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="changing" @click="changePassword">
                修改密码
              </el-button>
              <el-button @click="resetPasswordForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane label="通知设置" name="notification">
          <el-form
            ref="notificationFormRef"
            :model="notificationForm"
            label-width="120px"
            style="max-width: 500px"
          >
            <el-form-item label="邮件通知">
              <el-switch v-model="notificationForm.email_enabled" />
            </el-form-item>

            <el-form-item label="接收邮箱" v-if="notificationForm.email_enabled">
              <el-input v-model="notificationForm.email" placeholder="请输入邮箱" />
            </el-form-item>

            <el-form-item label="短信通知">
              <el-switch v-model="notificationForm.sms_enabled" />
            </el-form-item>

            <el-form-item label="手机号码" v-if="notificationForm.sms_enabled">
              <el-input v-model="notificationForm.phone" placeholder="请输入手机号" />
            </el-form-item>

            <el-form-item label="Webhook通知">
              <el-switch v-model="notificationForm.webhook_enabled" />
            </el-form-item>

            <el-form-item label="Webhook URL" v-if="notificationForm.webhook_enabled">
              <el-input v-model="notificationForm.webhook_url" placeholder="请输入Webhook地址" />
            </el-form-item>

            <el-form-item label="告警级别">
              <el-checkbox-group v-model="notificationForm.alert_levels">
                <el-checkbox value="critical" label="严重" />
                <el-checkbox value="warning" label="警告" />
                <el-checkbox value="info" label="提示" />
              </el-checkbox-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="savingNotify" @click="saveNotification">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import { getProfile, updateProfile, changePassword as changePasswordApi } from '@/api/user'
import { getNotificationSettings, updateNotificationSettings } from '@/api/user'

const activeTab = ref('basic')
const saving = ref(false)
const changing = ref(false)
const savingNotify = ref(false)

const profileFormRef = ref(null)
const passwordFormRef = ref(null)

// 基本资料
const profileForm = reactive({
  username: '',
  name: '',
  email: '',
  phone: '',
  avatar: '',
  role: ''
})

const profileRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

// 修改密码
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 通知设置
const notificationForm = reactive({
  email_enabled: true,
  email: '',
  sms_enabled: false,
  phone: '',
  webhook_enabled: false,
  webhook_url: '',
  alert_levels: ['critical', 'warning']
})

// 加载用户资料
const loadProfile = async () => {
  try {
    const res = await getProfile()
    Object.assign(profileForm, res.profile)
  } catch (error) {
    ElMessage.error('加载用户资料失败')
  }
}

// 保存资料
const saveProfile = async () => {
  if (!profileFormRef.value) return

  await profileFormRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const res = await updateProfile({
        name: profileForm.name,
        email: profileForm.email,
        phone: profileForm.phone,
        avatar: profileForm.avatar  // 可能是 Base64 或已有路径
      })

      // 正确更新所有字段
      profileForm.username = res.profile.username
      profileForm.name = res.profile.name
      profileForm.email = res.profile.email
      profileForm.phone = res.profile.phone
      profileForm.avatar = res.profile.avatar  // 更新为服务器返回的路径
      profileForm.role = res.profile.role

      // 更新本地存储的用户信息
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      user.name = profileForm.name
      user.email = profileForm.email
      user.phone = profileForm.phone
      user.avatar = profileForm.avatar  // 也保存头像路径
      localStorage.setItem('user', JSON.stringify(user))

      ElMessage.success('资料保存成功')
    } catch (error) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

// 重置资料
const resetProfile = () => {
  loadProfile()
}

// 修改密码
const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    changing.value = true
    try {
      await changePasswordApi({
        oldPassword: passwordForm.oldPassword,
        newPassword: passwordForm.newPassword
      })
      ElMessage.success('密码修改成功')
      resetPasswordForm()
    } catch (error) {
      ElMessage.error(error.message || '密码修改失败')
    } finally {
      changing.value = false
    }
  })
}

// 重置密码表单
const resetPasswordForm = () => {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  passwordFormRef.value?.clearValidate()
}

// 加载通知设置
const loadNotificationSettings = async () => {
  try {
    const res = await getNotificationSettings()
    Object.assign(notificationForm, res.settings)
  } catch (error) {
    console.error('加载通知设置失败:', error)
  }
}

// 保存通知设置
const saveNotification = async () => {
  savingNotify.value = true
  try {
    await updateNotificationSettings(notificationForm)
    ElMessage.success('通知设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingNotify.value = false
  }
}

// 头像上传
const handleAvatarUpload = (file) => {
  // 模拟头像上传
  const reader = new FileReader()
  reader.onload = (e) => {
    profileForm.avatar = e.target.result
  }
  reader.readAsDataURL(file)
  return false
}

onMounted(() => {
  loadProfile()
  loadNotificationSettings()
})
</script>

<style scoped>
.profile-container {
  padding: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 16px;
  font-weight: bold;
}

.avatar-uploader {
  display: flex;
  align-items: center;
}

:deep(.el-tabs__content) {
  padding: 20px 0;
}
</style>