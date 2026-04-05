<template>
  <div class="analytics-page">
    <h1 class="page-title">📈 数据分析 Analytics</h1>
    <p class="page-desc">论文实验数据可视化与对比分析</p>

    <!-- 对比实验图表 -->
    <el-card class="chart-card comparison-card">
      <template #header>
        <div class="card-header">
          <span>📊 实验对比 Experiment Comparison</span>
          <el-button type="primary" text @click="loadComparisonData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div class="charts-row three-charts">
        <div class="chart-wrapper">
          <div ref="responseTimeChartRef" class="chart-inner"></div>
        </div>
        <div class="chart-wrapper">
          <div ref="accuracyChartRef" class="chart-inner"></div>
        </div>
        <div class="chart-wrapper">
          <div ref="costChartRef" class="chart-inner"></div>
        </div>
      </div>

      <!-- 详细数据表格 -->
      <el-table :data="comparisonData.detailed_metrics" style="margin-top: 20px" size="small">
        <el-table-column prop="mode" label="实验模式" width="120">
          <template #default="{ row }">
            <el-tag :type="getModeTagType(row.mode)" effect="light">
              {{ getModeLabel(row.mode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="avg_response_time" label="平均响应时间(ms)" />
        <el-table-column prop="accuracy" label="准确率(%)" />
        <el-table-column prop="total_queries" label="查询次数" />
        <el-table-column prop="cloud_cost" label="云端成本($)" />
      </el-table>
    </el-card>

    <!-- 迭代进度图表 -->
    <el-card class="chart-card iteration-card">
      <template #header>
        <div class="card-header">
          <span>🔄 自我迭代进度 Self-Iteration Progress</span>
          <el-radio-group v-model="iterationDays" size="small" @change="loadIterationData">
            <el-radio-button :value="7">7天</el-radio-button>
            <el-radio-button :value="30">30天</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      
      <div class="chart-wrapper large">
        <div ref="iterationChartRef" class="chart-inner"></div>
      </div>
    </el-card>

    <!-- 专家分布 -->
    <el-card class="chart-card expert-card">
      <template #header>
        <div class="card-header">
          <span>🎓 专家池分布 Expert Distribution</span>
        </div>
      </template>
      
      <div class="charts-row two-charts">
        <div class="chart-wrapper">
          <div ref="expertPieChartRef" class="chart-inner"></div>
        </div>
        <div class="chart-wrapper">
          <div ref="expertBarChartRef" class="chart-inner"></div>
        </div>
      </div>
    </el-card>

    <!-- 实验结论（基于真实数据动态计算） -->
    <el-card class="conclusion-card">
      <template #header>
        <span>📝 实验数据概览 Overview</span>
      </template>
      <div class="conclusions">
        <div class="conclusion-item">
          <div class="conclusion-number">1</div>
          <div class="conclusion-content">
            <h4>总会话数量</h4>
            <p>系统累计处理了 <strong>{{ comparisonData.detailed_metrics.reduce((sum, m) => sum + (m.total_queries || 0), 0) }}</strong> 次问答交互</p>
          </div>
        </div>
        <div class="conclusion-item">
          <div class="conclusion-number">2</div>
          <div class="conclusion-content">
            <h4>平均响应时间</h4>
            <p>全系统平均响应时间为 <strong>{{ Math.round(comparisonData.detailed_metrics.reduce((sum, m) => sum + (m.avg_response_time || 0), 0) / (comparisonData.detailed_metrics.length || 1)) }}ms</strong></p>
          </div>
        </div>
        <div class="conclusion-item">
          <div class="conclusion-number">3</div>
          <div class="conclusion-content">
            <h4>知识库总量</h4>
            <p>当前知识库共有 <strong>{{ iterationData.knowledge_growth[iterationData.knowledge_growth.length - 1] || 0 }}</strong> 条知识点</p>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { experimentApi } from '../api'

// 图表实例
let responseTimeChart: echarts.ECharts | null = null
let accuracyChart: echarts.ECharts | null = null
let costChart: echarts.ECharts | null = null
let iterationChart: echarts.ECharts | null = null
let expertPieChart: echarts.ECharts | null = null
let expertBarChart: echarts.ECharts | null = null

const responseTimeChartRef = ref<HTMLElement>()
const accuracyChartRef = ref<HTMLElement>()
const costChartRef = ref<HTMLElement>()
const iterationChartRef = ref<HTMLElement>()
const expertPieChartRef = ref<HTMLElement>()
const expertBarChartRef = ref<HTMLElement>()

// 数据
const comparisonData = ref({
  modes: [],
  avg_response_time: [],
  accuracy: [],
  cost_per_query: [],
  detailed_metrics: []
})
const iterationDays = ref(30)
const iterationData = ref({ dates: [], knowledge_growth: [], accuracy_improvement: [], cloud_cost_reduction: [] })
const expertStats = ref([])

function getModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    'baseline': '基线组',
    'rag_only': 'RAG组',
    'expert_routing': '专家路由组',
    'full_system': '完整系统'
  }
  return labels[mode] || mode
}

function getModeTagType(mode: string): string {
  const types: Record<string, string> = {
    'baseline': 'info',
    'rag_only': 'warning',
    'expert_routing': 'primary',
    'full_system': 'success'
  }
  return types[mode] || ''
}

// 孟菲斯配色
const colors = ['#FF78A5', '#FFF14F', '#4CC9BB', '#F28E70']

function initCharts() {
  try {
    if (responseTimeChartRef.value) {
      responseTimeChart = echarts.init(responseTimeChartRef.value, undefined, { renderer: 'canvas' })
    }
    if (accuracyChartRef.value) {
      accuracyChart = echarts.init(accuracyChartRef.value, undefined, { renderer: 'canvas' })
    }
    if (costChartRef.value) {
      costChart = echarts.init(costChartRef.value, undefined, { renderer: 'canvas' })
    }
    if (iterationChartRef.value) {
      iterationChart = echarts.init(iterationChartRef.value, undefined, { renderer: 'canvas' })
    }
    if (expertPieChartRef.value) {
      expertPieChart = echarts.init(expertPieChartRef.value, undefined, { renderer: 'canvas' })
    }
    if (expertBarChartRef.value) {
      expertBarChart = echarts.init(expertBarChartRef.value, undefined, { renderer: 'canvas' })
    }
    
    window.addEventListener('resize', handleResize)
  } catch (error) {
    console.error('图表初始化失败:', error)
  }
}

function handleResize() {
  try {
    responseTimeChart?.resize()
    accuracyChart?.resize()
    costChart?.resize()
    iterationChart?.resize()
    expertPieChart?.resize()
    expertBarChart?.resize()
  } catch (error) {
    // 忽略resize错误
  }
}

async function loadComparisonData() {
  try {
    const res: any = await experimentApi.getComparison()
    if (res.code === 200) {
      comparisonData.value = res.data
      
      if (!responseTimeChart || !accuracyChart || !costChart) {
        initCharts()
      }
      
      // 更新响应时间图表
      responseTimeChart?.setOption({
        title: { text: '响应时间', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 40, bottom: 30, left: 50, right: 20 },
        color: colors,
        xAxis: { type: 'category', data: res.data.modes.map(getModeLabel) },
        yAxis: { type: 'value', name: 'ms' },
        series: [{
          data: res.data.avg_response_time,
          type: 'bar',
          itemStyle: { borderWidth: 2, borderColor: '#111' }
        }]
      })
      
      // 更新准确率图表
      accuracyChart?.setOption({
        title: { text: '准确率', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 40, bottom: 30, left: 50, right: 20 },
        color: colors,
        xAxis: { type: 'category', data: res.data.modes.map(getModeLabel) },
        yAxis: { type: 'value', max: 100, name: '%' },
        series: [{
          data: res.data.accuracy,
          type: 'bar',
          itemStyle: { borderWidth: 2, borderColor: '#111' }
        }]
      })
      
      // 更新成本图表
      costChart?.setOption({
        title: { text: '单次查询成本', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 40, bottom: 30, left: 50, right: 20 },
        color: colors,
        xAxis: { type: 'category', data: res.data.modes.map(getModeLabel) },
        yAxis: { type: 'value', name: '$' },
        series: [{
          data: res.data.cost_per_query,
          type: 'bar',
          itemStyle: { borderWidth: 2, borderColor: '#111' }
        }]
      })
    }
  } catch (error) {
    console.error('加载对比数据失败:', error)
  }
}

async function loadIterationData() {
  try {
    const res: any = await experimentApi.getIterationProgress(iterationDays.value)
    if (res.code === 200) {
      iterationData.value = res.data
      
      if (!iterationChart) {
        initCharts()
      }
      
      iterationChart?.setOption({
        title: { text: '30天迭代趋势', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 50, bottom: 80, left: 60, right: 60 },
        legend: { bottom: 10, data: ['知识库增长', '准确率提升', '云端成本占比'] },
        color: colors,
        xAxis: { type: 'category', data: res.data.dates },
        yAxis: [
          { type: 'value', name: '数量', position: 'left' },
          { type: 'value', name: '%', position: 'right' }
        ],
        series: [
          { name: '知识库增长', data: res.data.knowledge_growth, type: 'line', smooth: true },
          { name: '准确率提升', data: res.data.accuracy_improvement, type: 'line', smooth: true, yAxisIndex: 1 },
          { name: '云端成本占比', data: res.data.cloud_cost_reduction, type: 'line', smooth: true, yAxisIndex: 1 }
        ]
      })
    }
  } catch (error) {
    console.error('加载迭代数据失败:', error)
  }
}

async function loadExpertStats() {
  try {
    const res: any = await experimentApi.getDashboard()
    if (res.code === 200) {
      expertStats.value = res.data.expert_distribution
      
      const data = res.data.expert_distribution.map((item: any) => ({
        name: item.name,
        value: item.count
      }))
      
      if (!expertPieChart || !expertBarChart) {
        initCharts()
      }
      
      expertPieChart?.setOption({
        title: { text: '问答分布', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 40, bottom: 20 },
        color: colors,
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '55%'],
          data: data,
          itemStyle: { borderWidth: 2, borderColor: '#111' }
        }]
      })
      
      expertBarChart?.setOption({
        title: { text: '专家活跃度', left: 'center', textStyle: { fontFamily: 'Space Grotesk' } },
        grid: { top: 40, bottom: 60, left: 60, right: 20 },
        color: colors,
        xAxis: { type: 'category', data: data.map((d: any) => d.name), axisLabel: { rotate: 30 } },
        yAxis: { type: 'value' },
        series: [{
          data: data.map((d: any) => d.value),
          type: 'bar',
          itemStyle: { borderWidth: 2, borderColor: '#111' }
        }]
      })
    }
  } catch (error) {
    console.error('加载专家统计失败:', error)
  }
}

onMounted(async () => {
  await nextTick()
  initCharts()
  
  await Promise.all([
    loadComparisonData(),
    loadIterationData(),
    loadExpertStats()
  ])
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  try {
    responseTimeChart?.dispose()
    responseTimeChart = null
  } catch (e) {}
  
  try {
    accuracyChart?.dispose()
    accuracyChart = null
  } catch (e) {}
  
  try {
    costChart?.dispose()
    costChart = null
  } catch (e) {}
  
  try {
    iterationChart?.dispose()
    iterationChart = null
  } catch (e) {}
  
  try {
    expertPieChart?.dispose()
    expertPieChart = null
  } catch (e) {}
  
  try {
    expertBarChart?.dispose()
    expertBarChart = null
  } catch (e) {}
})
</script>

<style scoped lang="scss">
.analytics-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
}

.page-title {
  font-family: var(--font-display);
  font-size: clamp(18px, 2.5vh, 28px);
  font-weight: 700;
  margin: 0;
  text-transform: uppercase;
  flex-shrink: 0;
}
.page-desc {
  color: #666;
  margin: 0 0 8px 0;
  font-size: clamp(12px, 1.8vh, 14px);
  flex-shrink: 0;
}

.chart-card {
  flex-shrink: 0;
  margin-bottom: 0;
  
  :deep(.el-card__body) {
    padding: 16px;
  }
}

.comparison-card {
  min-height: 400px;
}

.iteration-card {
  min-height: 380px;
}

.expert-card {
  min-height: 350px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-display);
  font-weight: 700;
  text-transform: uppercase;
  font-size: clamp(12px, 2vh, 16px);
}

.charts-row {
  display: grid;
  gap: 16px;
  width: 100%;
}

.three-charts {
  grid-template-columns: repeat(3, 1fr);
}

.two-charts {
  grid-template-columns: repeat(2, 1fr);
}

.chart-wrapper {
  position: relative;
  width: 100%;
  height: 250px;
  
  &.large {
    height: 300px;
  }
}

.chart-inner {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
}

.conclusion-card {
  flex-shrink: 0;
  margin-bottom: 0;
  
  :deep(.el-card__body) {
    padding: 12px 16px;
  }
}

.conclusions {
  display: flex;
  flex-direction: row;
  gap: 16px;
}

.conclusion-item {
  flex: 1;
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #f9f9f9;
  border: 2px solid #eee;
  min-width: 0;
}

.conclusion-number {
  width: 32px;
  height: 32px;
  background: var(--memphis-pink);
  border: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.conclusion-content h4 {
  font-family: var(--font-display);
  font-size: clamp(12px, 1.8vh, 14px);
  font-weight: 700;
  margin: 0 0 4px 0;
}

.conclusion-content p {
  margin: 0;
  color: #666;
  font-size: clamp(11px, 1.5vh, 13px);
}

@media (max-width: 1200px) {
  .three-charts {
    grid-template-columns: repeat(2, 1fr);
  }
  .two-charts {
    grid-template-columns: 1fr;
  }
  .conclusions {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .three-charts {
    grid-template-columns: 1fr;
  }
  .chart-wrapper {
    height: 200px;
  }
}
</style>
