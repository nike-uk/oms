<template>
  <div class="topology">
    <el-card>
      <template #header>
        <div class="header">
          <span>服务拓扑图</span>
          <div>
            <el-button @click="resetZoom">
              <el-icon><RefreshRight /></el-icon>
              重置视图
            </el-button>
            <el-button type="primary" @click="loadTopology">
              <el-icon><Loading /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="topology-container">
        <div ref="graphContainer" class="graph"></div>

        <!-- 图例 -->
        <div class="legend">
          <div class="legend-item">
            <span class="legend-dot healthy"></span>
            <span>健康</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot warning"></span>
            <span>警告</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot critical"></span>
            <span>严重</span>
          </div>
        </div>

        <!-- 节点信息面板 -->
        <div v-if="selectedNode" class="node-panel">
          <h4>{{ selectedNode.name }}</h4>
          <el-divider />
          <p><strong>状态：</strong>
            <el-tag :type="getStatusType(selectedNode.status)">
              {{ getStatusText(selectedNode.status) }}
            </el-tag>
          </p>
          <p><strong>CPU：</strong> {{ selectedNode.metrics?.cpu || '-' }}%</p>
          <p><strong>内存：</strong> {{ selectedNode.metrics?.memory || '-' }}%</p>
          <p><strong>延迟：</strong> {{ selectedNode.metrics?.latency || '-' }}ms</p>
          <el-divider />
          <el-button type="primary" size="small" @click="viewServiceDetail">
            查看详情
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getTopology } from '@/api'

const router = useRouter()
const graphContainer = ref(null)
const selectedNode = ref(null)

let chartInstance = null

// 服务指标Mock数据
const serviceMetrics = {
  'api-gateway': { cpu: 45.2, memory: 62.1, latency: 120 },
  'user-service': { cpu: 32.5, memory: 48.3, latency: 85 },
  'order-service': { cpu: 78.9, memory: 72.4, latency: 450 },
  'payment-service': { cpu: 25.1, memory: 35.7, latency: 95 },
  'inventory-service': { cpu: 18.3, memory: 28.9, latency: 60 }
}

const getStatusType = (status) => {
  const map = { healthy: 'success', warning: 'warning', critical: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { healthy: '健康', warning: '警告', critical: '严重' }
  return map[status] || status
}

const getNodeColor = (status) => {
  const map = { healthy: '#67c23a', warning: '#e6a23c', critical: '#f56c6c' }
  return map[status] || '#909399'
}

const initGraph = (data) => {
  if (!graphContainer.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(graphContainer.value)
  }

  // 构建节点
  const nodes = data.nodes.map(node => ({
    id: node.id,
    name: node.name,
    symbolSize: 50,
    itemStyle: {
      color: getNodeColor(node.status),
      borderColor: '#fff',
      borderWidth: 2,
      shadowBlur: 10,
      shadowColor: getNodeColor(node.status)
    },
    label: {
      show: true,
      fontSize: 12,
      fontWeight: 'bold'
    },
    // 存储额外数据
    data: {
      status: node.status,
      metrics: serviceMetrics[node.id]
    }
  }))

  // 构建边
  const edges = data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    lineStyle: {
      color: '#909399',
      width: 2,
      curveness: 0.2,
      type: 'solid'
    },
    label: {
      show: true,
      formatter: edge.label || 'calls',
      fontSize: 10
    }
  }))

  const option = {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          const node = nodes.find(n => n.id === params.data.id)
          const metrics = node?.data?.metrics || {}
          return `
            <strong>${params.name}</strong><br/>
            状态: ${getStatusText(node?.data?.status || 'unknown')}<br/>
            CPU: ${metrics.cpu || '-'}%<br/>
            内存: ${metrics.memory || '-'}%<br/>
            延迟: ${metrics.latency || '-'}ms
          `
        }
        return `${params.data.source} → ${params.data.target}`
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      force: {
        repulsion: 500,
        edgeLength: 200,
        gravity: 0.1,
        friction: 0.1
      },
      roam: true,
      draggable: true,
      data: nodes,
      edges: edges,
      lineStyle: {
        color: '#909399',
        width: 2,
        curveness: 0.2
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 3,
          color: '#409EFF'
        }
      },
      // 节点样式
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
      },
      label: {
        show: true,
        position: 'bottom',
        offset: [0, 10],
        fontSize: 12,
        color: '#303133'
      }
    }]
  }

  chartInstance.setOption(option)

  // 绑定点击事件
  chartInstance.on('click', (params) => {
    if (params.dataType === 'node') {
      const node = nodes.find(n => n.id === params.data.id)
      selectedNode.value = {
        id: params.data.id,
        name: params.name,
        status: node?.data?.status || 'unknown',
        metrics: node?.data?.metrics || {}
      }
    } else {
      selectedNode.value = null
    }
  })
}

const loadTopology = async () => {
  try {
    const res = await getTopology()
    initGraph(res)
  } catch (error) {
    ElMessage.error('加载拓扑数据失败')
    // 使用Mock数据
    initGraph({
      nodes: [
        { id: 'api-gateway', name: 'API Gateway', status: 'warning' },
        { id: 'user-service', name: 'User Service', status: 'healthy' },
        { id: 'order-service', name: 'Order Service', status: 'critical' },
        { id: 'payment-service', name: 'Payment Service', status: 'healthy' },
        { id: 'inventory-service', name: 'Inventory Service', status: 'healthy' }
      ],
      edges: [
        { source: 'api-gateway', target: 'user-service', label: 'calls' },
        { source: 'api-gateway', target: 'order-service', label: 'calls' },
        { source: 'api-gateway', target: 'payment-service', label: 'calls' },
        { source: 'order-service', target: 'user-service', label: 'calls' },
        { source: 'order-service', target: 'inventory-service', label: 'calls' },
        { source: 'payment-service', target: 'user-service', label: 'calls' }
      ]
    })
  }
}

const resetZoom = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: 'restore'
    })
  }
}

const viewServiceDetail = () => {
  if (selectedNode.value) {
    // 跳转到告警列表，筛选该服务
    router.push({
      path: '/alerts',
      query: { service: selectedNode.value.id }
    })
  }
}

// 窗口大小变化时重绘
const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  loadTopology()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.topology {
  padding: 0;
  height: calc(100vh - 120px);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.topology-container {
  position: relative;
  height: calc(100vh - 200px);
  min-height: 500px;
}

.graph {
  width: 100%;
  height: 100%;
}

.legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 10px 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.healthy {
  background: #67c23a;
}

.legend-dot.warning {
  background: #e6a23c;
}

.legend-dot.critical {
  background: #f56c6c;
}

.node-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  width: 200px;
}

.node-panel h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.node-panel p {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
}
</style>