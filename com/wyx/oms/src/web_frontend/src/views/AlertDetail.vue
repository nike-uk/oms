<template>
  <div class="alert-detail">
    <el-page-header @back="$router.push('/alerts')" title="返回">
      <template #content>
        <span class="page-title">告警详情 #{{ alert.id }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：告警信息和指标图表 -->
      <el-col :span="16">
        <!-- 告警基本信息 -->
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <span>告警信息</span>
              <div>
                <el-tag :type="getSeverityType(alert.severity)" size="large">
                  {{ getSeverityText(alert.severity) }}
                </el-tag>
                <el-tag :type="getStatusType(alert.status)" size="large" style="margin-left: 10px">
                  {{ getStatusText(alert.status) }}
                </el-tag>
              </div>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="服务名称">{{ alert.service_name }}</el-descriptions-item>
            <el-descriptions-item label="异常指标">{{ getMetricLabel(alert.metric_name) }}</el-descriptions-item>
            <el-descriptions-item label="当前值">
              <span :class="['value-highlight', alert.severity]">
                {{ formatValue(alert.metric_value, alert.metric_name) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="异常分数">
              <el-progress
                :percentage="Math.round((alert.anomaly_score || 0) * 100)"
                :color="getScoreColor(alert.anomaly_score)"
                :stroke-width="10"
                style="width: 150px"
              />
            </el-descriptions-item>
            <el-descriptions-item label="发生时间">{{ formatTime(alert.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="确认时间">{{ formatTime(alert.confirmed_at) || '未确认' }}</el-descriptions-item>
            <el-descriptions-item label="告警描述" :span="2">{{ alert.description }}</el-descriptions-item>
          </el-descriptions>

          <!-- 操作按钮 -->
          <div class="actions">
            <el-button
              v-if="alert.status === 'pending'"
              type="primary"
              @click="updateStatus('confirmed')"
            >
              <el-icon><Check /></el-icon>
              确认告警
            </el-button>
            <el-button
              v-if="alert.status !== 'resolved'"
              type="success"
              @click="updateStatus('resolved')"
            >
              <el-icon><CircleCheck /></el-icon>
              标记为解决
            </el-button>
            <el-button type="info" @click="analyzeLogs" :loading="analyzing">
              <el-icon><ChatDotRound /></el-icon>
              LLM智能分析
            </el-button>
          </div>
        </el-card>

        <!-- 指标趋势图 -->
        <el-card class="chart-card">
          <template #header>
            <span>{{ getMetricLabel(alert.metric_name) }} - 历史趋势</span>
          </template>
          <div ref="metricChart" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- 右侧：LLM诊断和相关日志 -->
      <el-col :span="8">
        <!-- LLM智能诊断 -->
        <el-card class="diagnosis-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><MagicStick /></el-icon> AI智能诊断</span>
              <div>
                <el-tag v-if="alert.llm_diagnosis" type="success" size="small">已分析</el-tag>
                <el-button
                  v-if="alert.llm_diagnosis"
                  type="primary"
                  link
                  @click="copyDiagnosis"
                  style="margin-left: 8px"
                >
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="alert.llm_diagnosis" class="diagnosis-content">
            <div v-html="renderedMarkdown" class="markdown-body"></div>
          </div>
          <div v-else class="empty-diagnosis">
            <el-icon :size="40"><Document /></el-icon>
            <p>暂无智能诊断结果</p>
            <el-button type="primary" @click="analyzeLogs" :loading="analyzing">
              开始分析
            </el-button>
          </div>
        </el-card>

        <!-- 影响范围 -->
        <el-card class="affected-card">
          <template #header>
            <span><el-icon><Connection /></el-icon> 影响范围</span>
          </template>

          <div v-if="alert.affected_services && alert.affected_services.length" class="affected-services">
            <el-tag
              v-for="service in alert.affected_services"
              :key="service"
              type="warning"
              style="margin: 5px"
            >
              {{ service }}
            </el-tag>
          </div>
          <div v-else class="empty-text">无关联服务</div>
        </el-card>

        <!-- 相关日志 -->
        <el-card class="logs-card">
          <template #header>
            <span><el-icon><Tickets /></el-icon> 相关日志</span>
          </template>

          <div class="logs-container">
            <div
              v-for="(log, index) in alert.related_logs"
              :key="index"
              :class="['log-item', log.level.toLowerCase()]"
            >
              <div class="log-time">{{ formatTime(log.timestamp) }}</div>
              <div class="log-level">{{ log.level }}</div>
              <div class="log-message">{{ log.message }}</div>
            </div>
            <div v-if="!alert.related_logs || !alert.related_logs.length" class="empty-text">
              暂无相关日志
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { getAlertDetail, updateAlertStatus, analyzeLogs as analyzeLogsApi } from '@/api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const alert = ref({})
const analyzing = ref(false)
const metricChart = ref(null)
let chartInstance = null

// 配置 marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

// 渲染 Markdown
const renderedMarkdown = computed(() => {
  if (!alert.value.llm_diagnosis) return ''
  try {
    return marked.parse(alert.value.llm_diagnosis)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return `<pre>${alert.value.llm_diagnosis}</pre>`
  }
})

const getMetricLabel = (metric) => {
  if (!metric) return '未知指标'
  const map = {
    cpu_usage: 'CPU使用率',
    memory_usage: '内存使用率',
    request_latency: '请求延迟',
    error_rate: '错误率'
  }
  return map[metric] || metric
}

const formatValue = (value, metric) => {
  // 添加空值检查
  if (value === undefined || value === null) {
    return '-'
  }

  // 确保 value 是数字
  const numValue = Number(value)
  if (isNaN(numValue)) {
    return String(value)
  }

  if (metric === 'cpu_usage' || metric === 'memory_usage' || metric === 'error_rate') {
    return numValue.toFixed(1) + '%'
  }
  if (metric === 'request_latency') {
    return numValue.toFixed(0) + 'ms'
  }
  return numValue.toFixed(2)
}

const getSeverityType = (severity) => {
  if (!severity) return 'info'
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[severity] || 'info'
}

const getSeverityText = (severity) => {
  if (!severity) return '未知'
  const map = { critical: '严重', warning: '警告', info: '提示' }
  return map[severity] || severity
}

const getStatusType = (status) => {
  if (!status) return 'info'
  const map = { pending: 'warning', confirmed: 'primary', resolved: 'success' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  if (!status) return '未知'
  const map = { pending: '待处理', confirmed: '已确认', resolved: '已解决' }
  return map[status] || status
}

const getScoreColor = (score) => {
  if (score === undefined || score === null) {
    return '#67c23a'  // 默认绿色
  }
  if (score > 0.7) return '#f56c6c'
  if (score > 0.4) return '#e6a23c'
  return '#67c23a'
}

const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm:ss')
}

const initChart = (data) => {
  if (!metricChart.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(metricChart.value)
  }

  const timestamps = data.map(d => dayjs(d.timestamp).format('HH:mm'))
  const values = data.map(d => d.value)

  // 标记异常点（这里简化处理，标记超出均值2倍标准差的点）
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
  const threshold = mean + 2 * std

  const markPoints = values
    .map((v, i) => v > threshold ? { coord: [i, v] } : null)
    .filter(p => p)

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: getMetricLabel(alert.value.metric_name)
    },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      },
      markPoint: {
        data: markPoints.map(p => ({
          coord: p.coord,
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: { color: '#f56c6c' }
        }))
      },
      markLine: {
        silent: true,
        lineStyle: { color: '#e6a23c', type: 'dashed' },
        data: [{ yAxis: threshold, name: '异常阈值' }]
      }
    }]
  }

  chartInstance.setOption(option)
}

const loadDetail = async () => {
  try {
    const id = route.params.id
    const res = await getAlertDetail(id)
    alert.value = res

    await nextTick()
    if (res.metric_history && res.metric_history.length) {
      initChart(res.metric_history)
    }
  } catch (error) {
    ElMessage.error('加载告警详情失败')
  }
}

const updateStatus = async (status) => {
  try {
    await updateAlertStatus(route.params.id, status)
    ElMessage.success(`告警状态已更新`)
    loadDetail()
  } catch (error) {
    ElMessage.error('更新状态失败')
  }
}

const analyzeLogs = async () => {
  analyzing.value = true
  try {
    const res = await analyzeLogsApi({
      service_name: alert.value.service_name,
      alert_id: alert.value.id
    })
    alert.value.llm_diagnosis = res.diagnosis
    alert.value.related_logs = res.logs
    ElMessage.success('智能分析完成')
  } catch (error) {
    ElMessage.error('智能分析失败')
  } finally {
    analyzing.value = false
  }
}

const copyDiagnosis = async () => {
  try {
    await navigator.clipboard.writeText(alert.value.llm_diagnosis)
    ElMessage.success('诊断内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  loadDetail()
})

window.addEventListener('resize', () => {
  chartInstance?.resize()
})
</script>

<style scoped>
.alert-detail {
  padding: 0;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.info-card, .chart-card, .diagnosis-card, .affected-card, .logs-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value-highlight {
  font-size: 18px;
  font-weight: bold;
}

.value-highlight.critical {
  color: #f56c6c;
}

.value-highlight.warning {
  color: #e6a23c;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.diagnosis-content {
  padding: 15px;
  background: #f0f9eb;
  border-radius: 8px;
  border-left: 4px solid #67c23a;
  max-height: 500px;
  overflow-y: auto;
}

/* Markdown 样式 */
.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h2) {
  font-size: 1.3em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.1em;
}

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 10px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 10px;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.markdown-body :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 10px;
}

.markdown-body :deep(pre code) {
  display: inline;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body :deep(blockquote) {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 10px 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #e6a23c;
}

.markdown-body :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #e1e4e8;
  border: 0;
}

.empty-diagnosis {
  text-align: center;
  padding: 30px;
  color: #909399;
}

.empty-diagnosis p {
  margin: 15px 0;
}

.affected-services {
  padding: 10px;
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  padding: 8px 10px;
  border-bottom: 1px solid #ebeef5;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.log-item.error {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.log-item.warn {
  background: #fdf6ec;
  border-left: 3px solid #e6a23c;
}

.log-time {
  color: #909399;
  margin-bottom: 3px;
}

.log-level {
  display: inline-block;
  font-weight: bold;
  margin-right: 10px;
}

.log-message {
  color: #303133;
  word-break: break-all;
}

.empty-text {
  text-align: center;
  padding: 30px;
  color: #909399;
}
</style>