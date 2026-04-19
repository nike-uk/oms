<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card" :class="stat.type">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="40"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span>最近7天告警趋势</span>
          </template>
          <div ref="trendChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>服务健康状态</span>
          </template>
          <div ref="healthChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 服务列表和最近告警 -->
    <el-row :gutter="20" class="bottom-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>服务监控概览</span>
          </template>
          <el-table :data="serviceHealth" stripe>
            <el-table-column prop="name" label="服务名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cpu" label="CPU" width="80">
              <template #default="{ row }">
                <span :style="{ color: row.cpu > 80 ? '#f56c6c' : '#606266' }">
                  {{ row.cpu }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="memory" label="内存" width="80">
              <template #default="{ row }">
                <span :style="{ color: row.memory > 85 ? '#f56c6c' : '#606266' }">
                  {{ row.memory }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="latency" label="延迟(ms)" width="100" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button type="primary" link @click="$router.push('/alerts')">
                查看更多 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" stripe>
            <el-table-column prop="service_name" label="服务" width="120" />
            <el-table-column prop="severity" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="primary" link @click="$router.push(`/alerts/${row.id}`)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getDashboardOverview } from '@/api'
import dayjs from 'dayjs'

// 统计数据
const stats = ref([
  { title: '服务总数', value: 0, icon: 'Monitor', type: 'info' },
  { title: '健康服务', value: 0, icon: 'CircleCheck', type: 'success' },
  { title: '异常服务', value: 0, icon: 'Warning', type: 'warning' },
  { title: '待处理告警', value: 0, icon: 'Bell', type: 'danger' }
])

const serviceHealth = ref([])
const recentAlerts = ref([])

const trendChart = ref(null)
const healthChart = ref(null)

let trendChartInstance = null
let healthChartInstance = null

const getStatusType = (status) => {
  const map = { healthy: 'success', warning: 'warning', critical: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { healthy: '健康', warning: '警告', critical: '严重' }
  return map[status] || status
}

const getSeverityType = (severity) => {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[severity] || 'info'
}

const formatTime = (time) => {
  return dayjs(time).format('MM-DD HH:mm')
}

const initTrendChart = (data) => {
  if (!trendChart.value) return

  if (!trendChartInstance) {
    trendChartInstance = echarts.init(trendChart.value)
  }

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['严重', '警告', '提示'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date)
    },
    yAxis: { type: 'value' },
    series: [
      { name: '严重', type: 'bar', stack: 'total', color: '#f56c6c', data: data.map(d => d.critical) },
      { name: '警告', type: 'bar', stack: 'total', color: '#e6a23c', data: data.map(d => d.warning) },
      { name: '提示', type: 'bar', stack: 'total', color: '#909399', data: data.map(d => d.info) }
    ]
  }

  trendChartInstance.setOption(option)
}

const initHealthChart = (data) => {
  if (!healthChart.value) return

  if (!healthChartInstance) {
    healthChartInstance = echarts.init(healthChart.value)
  }

  const healthy = data.filter(d => d.status === 'healthy').length
  const warning = data.filter(d => d.status === 'warning').length
  const critical = data.filter(d => d.status === 'critical').length

  const option = {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['50%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: { scale: true },
      data: [
        { value: healthy, name: '健康', itemStyle: { color: '#67c23a' } },
        { value: warning, name: '警告', itemStyle: { color: '#e6a23c' } },
        { value: critical, name: '严重', itemStyle: { color: '#f56c6c' } }
      ]
    }]
  }

  healthChartInstance.setOption(option)
}

const loadData = async () => {
  try {
    const res = await getDashboardOverview()

    stats.value[0].value = res.summary.total_services || 5
    stats.value[1].value = res.summary.healthy_services || 3
    stats.value[2].value = res.summary.critical_services || 1
    stats.value[3].value = res.summary.pending_alerts || 4

    serviceHealth.value = res.service_health || []
    recentAlerts.value = res.recent_alerts || []

    initTrendChart(res.alert_trends || [])
    initHealthChart(res.service_health || [])
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadData()
})

// 窗口大小变化时重绘图表
window.addEventListener('resize', () => {
  trendChartInstance?.resize()
  healthChartInstance?.resize()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-3px);
}

.stat-card.info { border-left: 4px solid #909399; }
.stat-card.success { border-left: 4px solid #67c23a; }
.stat-card.warning { border-left: 4px solid #e6a23c; }
.stat-card.danger { border-left: 4px solid #f56c6c; }

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-right: 15px;
}

.stat-card.info .stat-icon { background: rgba(144, 147, 153, 0.1); color: #909399; }
.stat-card.success .stat-icon { background: rgba(103, 194, 58, 0.1); color: #67c23a; }
.stat-card.warning .stat-icon { background: rgba(230, 162, 60, 0.1); color: #e6a23c; }
.stat-card.danger .stat-icon { background: rgba(245, 108, 108, 0.1); color: #f56c6c; }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 100%;
}

.bottom-row {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>