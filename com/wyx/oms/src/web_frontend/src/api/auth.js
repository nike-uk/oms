import api from './index'

// 登录
export const login = (data) => {
  return api.post('/auth/login', data)
}

// 登出
export const logout = () => {
  return api.post('/auth/logout')
}

// 获取当前用户
export const getCurrentUser = () => {
  return api.get('/auth/current')
}