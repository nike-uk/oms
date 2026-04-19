<template>
  <div class="alert-list">
    <el-card>
      <template #header>
        <div class="header">
          <span>告警列表</span>
          <el-button type="primary" @click="runAnomalyDetection" :loading="detecting">
            <el-icon><VideoPlay /></el-icon>
            执行异常检测
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="handleFilterChange">
          <el-option label="待处理" value="pending" />
          <el-option label="已确认" value="confirmed" />
          <el-option label="已解决" value="resolved" />
        </el-select>
        <el-select v-model="filters.severity" placeholder="级别" clearable style="width: 120px; margin-left: 10px" @change="handleFilterChange">
          <el-option label="严重" value="critical" />
          <el-option label="警告" value="warning" />
          <el-option label="提示" value="info" />
        </el-select>
        <el-select v-model="filters.service" placeholder="服务" clearable style="width: 150px; margin-left: 10px" @change="handleFilterChange">
          <el-option v-for="s in services" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="handleSearch" style="margin-left: 10px">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button @click="handleReset" style="margin-left: 10px">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>

      <!-- 告警表格 -->
      <el-table :data="alerts" stripe v-loading="loading" style="margin-top: 20px">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="service_name" label="服务" width="140" />
        <el-table-column prop="metric_name" label="指标" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getMetricLabel(row.metric_name) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric_value" label="当前值" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.severity === 'critical' ? '#f56c6c' : '#606266', fontWeight: 'bold' }">
              {{ formatValue(row.metric_value, row.metric_name) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="anomaly_score" label="异常分数" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round((row.anomaly_score || 0) * 100)"
              :color="getScoreColor(row.anomaly_score || 0)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发生时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/alerts/${row.id}`)">
              详情
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              type="success"
              link
              @click="updateStatus(row, 'confirmed')"
            >
              确认
            </el-button>
            <el-button
              v-if="row.status !== 'resolved'"
              type="warning"
              link
              @click="updateStatus(row, 'resolved')"
            >
              解决
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { getAlerts, updateAlertStatus, detectAnomaly } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const detecting = ref(false)
const alerts = ref([])
const total = ref(0)
const services = ref(['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service'])

const filters = reactive({
  status: '',
  severity: '',
  service: ''
})

const pagination = reactive({
  page: 1,
  size: 20
})

const getMetricLabel = (metric) => {
  const map = {
    cpu_usage: 'CPU使用率',
    memory_usage: '内存使用率',
    request_latency: '请求延迟',
    error_rate: '错误率'
  }
  return map[metric] || metric
}

const formatValue = (value, metric) => {
  if (value === undefined || value === null) return '-'
  if (metric === 'cpu_usage' || metric === 'memory_usage' || metric === 'error_rate') {
    return value.toFixed(1) + '%'
  }
  if (metric === 'request_latency') {
    return value.toFixed(0) + 'ms'
  }
  return value.toFixed(2)
}

const getSeverityType = (severity) => {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[severity] || 'info'
}

const getSeverityText = (severity) => {
  const map = { critical: '严重', warning: '警告', info: '提示' }
  return map[severity] || severity
}

const getStatusType = (status) => {
  const map = { pending: 'warning', confirmed: 'primary', resolved: 'success' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { pending: '待处理', confirmed: '已确认', resolved: '已解决' }
  return map[status] || status
}

const getScoreColor = (score) => {
  if (score > 0.7) return '#f56c6c'
  if (score > 0.4) return '#e6a23c'
  return '#67c23a'
}

const formatTime = (time) => {
  if (!time) return '-'
  try {
    return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
  } catch (error) {
    return '-'
  }
}

const loadAlerts = async () => {
  loading.value = true
  try {
    const params = {
      limit: pagination.size,
      offset: (pagination.page - 1) * pagination.size
    }

    // 只添加有值的筛选条件
    if (filters.status) params.status = filters.status
    if (filters.severity) params.severity = filters.severity
    if (filters.service) params.service = filters.service

    console.log('请求参数:', params) // 调试用

    const res = await getAlerts(params)

    // 确保数据安全，为每个告警补充默认值
    alerts.value = (res.alerts || []).map(alert => ({
      id: alert.id || 0,
      service_name: alert.service_name || 'unknown',
      metric_name: alert.metric_name || 'cpu_usage',
      metric_value: alert.metric_value ?? 0,
      anomaly_score: alert.anomaly_score ?? 0,
      severity: alert.severity || 'info',
      description: alert.description || '无描述',
      status: alert.status || 'pending',
      created_at: alert.created_at || new Date().toISOString(),
      confirmed_at: alert.confirmed_at || null,
      resolved_at: alert.resolved_at || null,
      llm_diagnosis: alert.llm_diagnosis || null,
      related_logs: alert.related_logs || [],
      affected_services: alert.affected_services || []
    }))

    total.value = res.total || 0
  } catch (error) {
    console.error('加载告警列表失败:', error)
    ElMessage.error('加载告警列表失败')
    alerts.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 筛选条件变化时重置到第一页
const handleFilterChange = () => {
  pagination.page = 1
  loadAlerts()
}

// 查询按钮
const handleSearch = () => {
  pagination.page = 1
  loadAlerts()
}

// 重置筛选条件
const handleReset = () => {
  filters.status = ''
  filters.severity = ''
  filters.service = ''
  pagination.page = 1
  loadAlerts()
}

// 分页大小变化
const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  loadAlerts()
}

// 页码变化
const handlePageChange = (page) => {
  pagination.page = page
  loadAlerts()
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const updateStatus = async (row, status) => {
  try {
    await updateAlertStatus(row.id, status)
    ElMessage.success(`告警状态已更新为${getStatusText(status)}`)
    loadAlerts() // 重新加载当前页
  } catch (error) {
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

const runAnomalyDetection = async () => {
  detecting.value = true
  try {
    const res = await detectAnomaly({})
    ElMessage.success(`异常检测完成，发现 ${res.alerts_generated || 0} 个异常`)
    loadAlerts() // 重新加载第一页
  } catch (error) {
    console.error('异常检测失败:', error)
    ElMessage.error('异常检测失败')
  } finally {
    detecting.value = false
  }
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped>
.alert-list {
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>