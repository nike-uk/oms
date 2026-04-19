import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器 - 添加 token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    console.log('API Request:', config.method.toUpperCase(), config.url)
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('API Response:', response.config.url, response.data)
    return response.data
  },
  error => {
    console.error('API Error:', error.config?.url, error.message)

    // 401 未授权，跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// 仪表盘
export const getDashboardOverview = () => api.get('/dashboard/overview')

// 告警
export const getAlerts = (params) => api.get('/alerts', { params })
export const getAlertDetail = (id) => api.get(`/alerts/${id}`)
export const updateAlertStatus = (id, status) => api.put(`/alerts/${id}/status`, { status })

// 拓扑
export const getTopology = () => api.get('/topology')

// 指标
export const getServiceMetrics = (serviceName, params) => api.get(`/metrics/${serviceName}`, { params })

// 异常检测
export const detectAnomaly = (params) => api.post('/detect/anomaly', params)

// 日志分析
export const analyzeLogs = (params) => api.post('/analyze/logs', params)

export default api

export * from './auth'
export * from './user'