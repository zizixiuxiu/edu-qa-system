<template>
  <div class="experiments-page">
    <h1 class="page-title">实验控制 Experiments</h1>

    <!-- 当前配置卡片 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>当前配置 Current Config</span>
          <el-tag :type="getModeType(currentMode)" size="large" effect="light">
            {{ appStore.experimentModeLabel }}
          </el-tag>
        </div>
      </template>
      
      <div class="config-grid">
        <div class="config-item">
          <span class="config-label">专家路由</span>
          <el-switch v-model="currentConfig.expert_routing" disabled />
        </div>
        <div class="config-item">
          <span class="config-label">知识检索 RAG</span>
          <el-switch v-model="currentConfig.rag" disabled />
        </div>
        <div class="config-item">
          <span class="config-label">自我迭代</span>
          <el-switch v-model="currentConfig.self_iteration" disabled />
        </div>
      </div>
    </el-card>

    <!-- 实验预设 -->
    <h2 class="section-title">实验预设 Presets</h2>
    <div class="presets-grid">
      <div
        v-for="(desc, key) in presets"
        :key="key"
        :class="['preset-card', { active: currentMode === key }]"
        @click="applyPreset(key)"
      >
        <h3>{{ getPresetLabel(key) }}</h3>
        <p>{{ desc }}</p>
        <el-tag v-if="currentMode === key" type="primary" size="small" effect="light" class="current-tag">当前</el-tag>
      </div>
    </div>

    <!-- 消融实验 -->
    <h2 class="section-title">消融实验 Ablation Studies</h2>
    <div class="ablation-grid">
      <el-card v-for="item in ablationConfigs" :key="item.key" class="ablation-card">
        <h4>{{ item.title }}</h4>
        <p>{{ item.desc }}</p>
        <el-button 
          type="primary" 
          @click="applyPreset(item.key)"
          :loading="isLoading"
        >
          应用配置
        </el-button>
      </el-card>
    </div>

    <!-- 数据导出 -->
    <h2 class="section-title">数据导出 Export Data</h2>
    <el-card>
      <div class="export-actions">
        <el-button type="success" @click="exportData('json')">
          <el-icon><Download /></el-icon>
          导出 JSON
        </el-button>
        <el-button type="warning" @click="exportData('csv')">
          <el-icon><Document /></el-icon>
          导出 CSV
        </el-button>
      </div>
      <p class="export-hint">导出数据包含所有会话记录，用于论文数据分析</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { experimentApi } from '../api'

const appStore = useAppStore()
const currentMode = ref('full_system')
const currentConfig = ref({
  expert_routing: true,
  rag: true,
  self_iteration: true,
  finetune: true
})
const presets = ref<Record<string, string>>({})
const isLoading = ref(false)

const ablationConfigs = [
  { key: 'ablation_no_iteration', title: '禁用自我迭代', desc: '关闭云端质检和知识库自动更新，测试自我迭代的效果' }
]

function getPresetLabel(key: string): string {
  const labels: Record<string, string> = {
    'baseline': '基线组',
    'rag_only': 'RAG组',
    'expert_routing': '专家路由组',
    'full_system': '完整系统',
    'ablation_no_iteration': '消融-无迭代'
  }
  return labels[key] || key
}

function getModeType(mode: string): string {
  const types: Record<string, string> = {
    'baseline': 'info',
    'rag_only': 'warning',
    'expert_routing': 'primary',
    'full_system': 'success'
  }
  return types[mode] || ''
}

onMounted(async () => {
  // 加载预设列表
  const res: any = await experimentApi.getPresets()
  if (res.code === 200) {
    presets.value = res.data
  }
  
  // 加载当前配置
  const configRes: any = await experimentApi.getCurrentConfig()
  if (configRes.code === 200) {
    currentConfig.value = configRes.data
    currentMode.value = configRes.data.mode
  }
})

async function applyPreset(preset: string) {
  isLoading.value = true
  try {
    const res: any = await experimentApi.setConfig(preset)
    if (res.code === 200) {
      currentMode.value = preset
      currentConfig.value = res.data.current
      appStore.currentExperimentMode = preset
      ElMessage.success('实验配置已更新')
    }
  } catch (error) {
    ElMessage.error('配置更新失败')
  } finally {
    isLoading.value = false
  }
}

async function exportData(format: string) {
  try {
    const res: any = await experimentApi.exportData(format)
    if (res.code === 200) {
      // 下载文件
      const blob = new Blob(
        [format === 'json' ? JSON.stringify(res.data, null, 2) : res.data.content],
        { type: format === 'json' ? 'application/json' : 'text/csv' }
      )
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `experiment_data.${format}`
      link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    }
  } catch (error) {
    ElMessage.error('导出失败')
  }
}
</script>

<style scoped lang="scss">
.experiments-page {
  max-width: 1200px;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 32px 0;
  text-transform: uppercase;
}

.section-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  text-transform: uppercase;
  margin: 40px 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 3px solid var(--memphis-black);
}

.config-card {
  margin-bottom: 32px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-display);
  font-weight: 700;
  text-transform: uppercase;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}
.config-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #f5f5f5;
  border: 2px solid #ddd;
}
.config-label {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 4px;
}
.preset-card {
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.preset-card:hover {
  transform: translate(-4px, -4px);
  box-shadow: var(--shadow-hover);
}
.preset-card.active {
  background: var(--memphis-yellow);
}
.preset-card h3 {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 8px 0;
  text-transform: uppercase;
}
.preset-card p {
  font-size: 13px;
  color: var(--memphis-black);
  font-weight: 500;
  margin: 0;
  opacity: 0.85;
}
.preset-card.active p {
  color: var(--memphis-black);
  opacity: 0.9;
  font-weight: 600;
}
.preset-card .current-tag {
  margin-top: 8px;
  font-weight: 600;
}

.ablation-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 4px;
}
.ablation-card {
  h4 {
    font-family: var(--font-display);
    font-size: 16px;
    font-weight: 700;
    margin: 0 0 8px 0;
  }
  p {
    font-size: 13px;
    color: #666;
    margin: 0 0 16px 0;
  }
}

.export-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}
.export-hint {
  font-size: 13px;
  color: #888;
  margin: 0;
}

@media (max-width: 1024px) {
  .config-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .presets-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .config-grid, .presets-grid, .ablation-grid {
    grid-template-columns: 1fr;
  }
}
</style>
