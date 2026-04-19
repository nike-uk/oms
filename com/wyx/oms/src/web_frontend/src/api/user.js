import api from './index'

// 获取用户资料
export const getProfile = () => {
  return api.get('/user/profile')
}

// 更新用户资料
export const updateProfile = (data) => {
  return api.put('/user/profile', data)
}

// 修改密码
export const changePassword = (data) => {
  return api.put('/user/password', data)
}

// 获取通知设置
export const getNotificationSettings = () => {
  return api.get('/user/notification')
}

// 更新通知设置
export const updateNotificationSettings = (data) => {
  return api.put('/user/notification', data)
}