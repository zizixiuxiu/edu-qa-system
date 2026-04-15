<template>
  <div class="experiments-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <el-icon size="28"><SetUp /></el-icon>
        <h1>实验队列管理</h1>
      </div>
      <p class="header-desc">创建多组实验队列，串行执行，自动对比结果</p>
    </div>

    <!-- 创建实验表单 -->
    <el-card class="create-card">
      <template #header>
        <div class="card-header">
          <span>
            <el-icon><Plus /></el-icon>
            添加实验组
          </span>
          <el-tag type="info" effect="light">第 {{ experimentForms.length + 1 }} 组</el-tag>
        </div>
      </template>

      <el-form :model="currentExperiment" label-position="top" class="experiment-form">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="实验名称">
              <el-input 
                v-model="currentExperiment.name" 
                placeholder="输入实验名称，如：RAG对比实验"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="随机种子">
              <el-input-number 
                v-model="currentExperiment.random_seed" 
                :min="1" 
                :max="999999"
                :controls="false"
                style="width: 100%"
              />
              <span class="form-hint">用于固定数据集shuffle，保证实验可复现</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="题目数量限制">
              <el-input-number 
                v-model="currentExperiment.max_questions" 
                :min="0" 
                :max="1000"
                :step="10"
                :controls="false"
                style="width: 100%"
                placeholder="0表示无限制"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学科筛选">
              <el-select 
                v-model="currentExperiment.subject" 
                placeholder="全部学科"
                clearable
                style="width: 100%"
              >
                <el-option label="全部学科" value="" />
                <el-option 
                  v-for="subject in availableSubjects" 
                  :key="subject"
                  :label="subject"
                  :value="subject"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年份筛选">
              <el-select 
                v-model="currentExperiment.year" 
                placeholder="全部年份"
                clearable
                style="width: 100%"
              >
                <el-option label="全部年份" value="" />
                <el-option label="2022" value="2022" />
                <el-option label="2021" value="2021" />
                <el-option label="2020" value="2020" />
                <el-option label="2019" value="2019" />
                <el-option label="2018" value="2018" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 简化版：RAG开关同时控制知识库检索 -->
          <el-col :span="8">
            <el-form-item>
              <template #label>
                <span class="switch-label">
                  <el-icon><Search /></el-icon>
                  RAG知识检索
                </span>
              </template>
              <el-switch 
                v-model="currentExperiment.use_rag"
                active-text="启用"
                inactive-text="禁用"
                size="large"
              />
              <span class="form-hint">启用后从知识库检索相关内容增强回答</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item>
              <template #label>
                <span class="switch-label">
                  <el-icon><SetUp /></el-icon>
                  专家路由
                </span>
              </template>
              <el-switch 
                v-model="currentExperiment.use_expert_routing"
                active-text="启用"
                inactive-text="禁用"
                size="large"
              />
              <span class="form-hint">启用后使用学科专家prompt，禁用则无角色prompt</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item>
              <template #label>
                <span class="switch-label">
                  <el-icon><Refresh /></el-icon>
                  启用迭代
                </span>
              </template>
              <el-switch 
                v-model="currentExperiment.enable_iteration"
                active-text="启用"
                inactive-text="禁用"
                size="large"
              />
              <span class="form-hint">启用后自动将答案入库（仅FullSystem启用）</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="addExperiment"
            :disabled="!currentExperiment.name"
            size="large"
          >
            <el-icon><Plus /></el-icon>
            添加到队列
          </el-button>
          <el-button @click="resetForm" size="large">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 实验队列列表 -->
    <el-card class="queue-card">
      <template #header>
        <div class="card-header">
          <span>
            <el-icon><List /></el-icon>
            实验队列
            <el-tag type="primary" effect="light" class="count-tag">
              {{ experimentQueue.length }} 组
            </el-tag>
          </span>
          <div class="header-actions">
            <el-tag v-if="queueStats.pending > 0" type="info" effect="light">
              待执行: {{ queueStats.pending }}
            </el-tag>
            <el-tag v-if="queueStats.running > 0" type="warning" effect="light">
              执行中: {{ queueStats.running }}
            </el-tag>
            <el-tag v-if="queueStats.completed > 0" type="success" effect="light">
              已完成: {{ queueStats.completed }}
            </el-tag>
            <el-button 
              type="danger" 
              link
              @click="clearQueue"
              :disabled="experimentQueue.length === 0 || isExecuting"
            >
              <el-icon><Delete /></el-icon>
              清空队列
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="experimentQueue" 
        stripe
        v-loading="loading"
        class="queue-table"
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column prop="name" label="实验名称" min-width="150">
          <template #default="{ row }">
            <div class="experiment-name">
              <el-icon><SetUp /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="light" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.progress || 0" 
              :status="row.progress === 100 ? 'success' : ''"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column label="配置" min-width="240">
          <template #default="{ row }">
            <div class="config-tags">
              <el-tag size="small" effect="light" type="info">
                种子: {{ row.config?.random_seed }}
              </el-tag>
              <!-- 简化版标签：只用两个核心开关 -->
              <el-tag size="small" :type="row.config?.use_expert_routing ? 'success' : 'info'" effect="light">
                路由{{ row.config?.use_expert_routing ? '✓' : '✗' }}
              </el-tag>
              <el-tag size="small" :type="row.config?.use_rag ? 'success' : 'info'" effect="light">
                RAG{{ row.config?.use_rag ? '✓' : '✗' }}
              </el-tag>
              <el-tag size="small" :type="row.config?.enable_iteration ? 'success' : 'warning'" effect="light">
                迭代{{ row.config?.enable_iteration ? '✓' : '✗' }}
              </el-tag>
              <el-tag v-if="row.config?.max_questions" size="small" type="warning" effect="light">
                {{ row.config?.max_questions }}题
              </el-tag>
              <el-tag v-if="row.config?.subject" size="small" type="primary" effect="light">
                {{ row.config?.subject }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row, $index }">
            <el-button 
              type="danger" 
              link
              size="small"
              @click="removeExperiment($index)"
              :disabled="row.status === 'running' || isExecuting"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty 
        v-if="experimentQueue.length === 0" 
        description="暂无实验组，请在上方添加"
        :image-size="100"
      />
    </el-card>

    <!-- 执行控制按钮 -->
    <div class="control-section">
      <el-card class="control-card">
        <div class="control-content">
          <div class="control-left">
            <el-button 
              type="primary" 
              size="large"
              @click="startExperiments"
              :loading="isStarting"
              :disabled="!canStart || isExecuting"
            >
              <el-icon><VideoPlay /></el-icon>
              {{ isStarting ? '启动中...' : '一键开始实验队列' }}
            </el-button>
            <el-button 
              type="danger" 
              size="large"
              @click="stopExperiments"
              :loading="isStopping"
              :disabled="!isExecuting"
            >
              <el-icon><VideoPause /></el-icon>
              {{ isStopping ? '停止中...' : '停止' }}
            </el-button>
          </div>
          <div class="control-right">
            <el-button 
              type="info" 
              size="large"
              @click="loadQueue"
              :loading="loading"
            >
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
            <el-button 
              type="warning" 
              size="large"
              @click="runAllExperiments"
              :loading="isStarting"
              :disabled="isExecuting || experimentQueue.length > 0"
            >
              <el-icon><MagicStick /></el-icon>
              一键运行全部实验
            </el-button>
            <el-button 
              type="success" 
              size="large"
              @click="goToResults"
              :disabled="!hasCompletedExperiments"
            >
              <el-icon><DataLine /></el-icon>
              查看结果
            </el-button>
          </div>
        </div>

        <!-- 执行提示 -->
        <el-alert 
          v-if="currentRunningExperiment" 
          :title="`正在执行: ${currentRunningExperiment.name}`"
          type="info"
          :closable="false"
          show-icon
          class="executing-alert"
        >
          <template #default>
            <div class="progress-detail">
              <span>题目 {{ currentRunningExperiment.current_question || 0 }} / {{ currentRunningExperiment.total_questions || 0 }}</span>
              <span class="progress-percent">{{ currentRunningExperiment.progress || 0 }}%</span>
            </div>
          </template>
        </el-alert>

        <!-- 状态说明 -->
        <div v-if="!canStart && experimentQueue.length > 0 && !isExecuting" class="status-hint">
          <el-alert 
            :title="statusHint"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>
    </div>

    <!-- 快速预设 -->
    <el-card class="preset-card">
      <template #header>
        <div class="card-header">
          <span>
            <el-icon><MagicStick /></el-icon>
            快速预设（论文实验）
          </span>
          <el-tag type="warning" effect="light">知识库初始为空，请按顺序执行</el-tag>
        </div>
      </template>
      <!-- 实验设计说明 -->
      <div class="preset-section">
        <div class="preset-title">📊 论文实验设计（对照组设置）</div>
        <div class="experiment-flow">
          <div class="flow-step">
            <div class="step-num">1</div>
            <div class="step-content">
              <strong>测量路由贡献（无知识库）</strong>
              <div class="step-detail">
                Baseline（无路由）vs ExpertOnly（有路由）<br>
                <span class="step-note">差异 = 专家路由独立贡献</span>
              </div>
            </div>
          </div>
          <div class="flow-arrow">↓ 积累知识库</div>
          <div class="flow-step">
            <div class="step-num">2</div>
            <div class="step-content">
              <strong>测量RAG贡献（有知识库后）</strong>
              <div class="step-detail">
                ExpertOnly（无RAG）vs RAGOnly（有RAG）<br>
                <span class="step-note">差异 = RAG独立贡献</span>
              </div>
            </div>
          </div>
          <div class="flow-arrow">↓ 运行完整系统</div>
          <div class="flow-step">
            <div class="step-num">3</div>
            <div class="step-content">
              <strong>测量自进化贡献（迭代对比）</strong>
              <div class="step-detail">
                FullSystem 第1轮 vs 第3轮<br>
                <span class="step-note">差异 = 自进化模块贡献</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <el-divider />
      
      <div class="preset-section">
        <div class="preset-title">📌 第一阶段：基线测量（无知识库，禁用迭代）</div>
        <div class="preset-buttons">
          <el-button type="primary" @click="applyPreset('phase1_baseline_expert')">
            <el-icon><SetUp /></el-icon>
            ① Baseline + ExpertOnly
          </el-button>
        </div>
        <div class="preset-hint">
          <strong>目的：</strong>测量专家路由的独立贡献<br>
          <strong>配置：</strong>禁用知识库、禁用RAG、禁用迭代（避免污染基线）<br>
          <strong>预期：</strong>ExpertOnly 准确率 > Baseline 准确率
        </div>
      </div>
      
      <el-divider />
      
      <div class="preset-section">
        <div class="preset-title">📌 第二阶段：RAG验证（依赖积累的知识库）</div>
        <div class="preset-buttons">
          <el-button type="success" @click="applyPreset('phase2_rag_fullsystem')">
            <el-icon><Collection /></el-icon>
            ② RAGOnly + FullSystem 1/2/3轮
          </el-button>
        </div>
        <div class="preset-hint">
          <strong>前提：</strong>第一阶段完成后，知识库有20+条数据<br>
          <strong>RAGOnly：</strong>测量RAG独立贡献（vs ExpertOnly）<br>
          <strong>FullSystem 1/2/3轮：</strong>测量自进化效果（迭代开关对比）<br>
          <strong>注意：</strong>前3轮启用迭代积累知识，之后可对比有无迭代的差异
        </div>
      </div>
      
      <el-divider />
      
      <div class="preset-section">
        <div class="preset-title">其他实验</div>
        <div class="preset-buttons">
          <el-button @click="applyPreset('rag_comparison')">
            <el-icon><Switch /></el-icon>
            RAG开关对比
          </el-button>
          <el-button @click="applyPreset('seed_robustness')">
            <el-icon><Refresh /></el-icon>
            随机种子鲁棒性
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  SetUp,
  Plus,
  List,
  Delete,
  VideoPlay,
  VideoPause,
  Refresh,
  DataLine,
  RefreshLeft,
  Collection,
  Search,
  MagicStick,
  Switch
} from '@element-plus/icons-vue'
import { experimentApi, expertApi, benchmarkApi } from '../api'

const router = useRouter()

// ============ 数据 ============

// 简化实验配置：use_rag 同时控制知识库和RAG检索
interface ExperimentConfig {
  name: string
  random_seed: number
  use_rag: boolean  // RAG知识检索（true=启用知识库+RAG，false=纯模型）
  use_expert_routing: boolean  // 专家路由（true=使用学科专家prompt，false=无角色prompt）
  enable_iteration: boolean  // 自动入库（仅FullSystem启用）
  max_questions: number | null
  subject: string | null
  year: string | null
  description?: string
  prompt_template?: string
}

interface ExperimentItem {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  config: ExperimentConfig
  progress: number
  current_question: number
  total_questions: number
  created_at: string
  started_at?: string
  completed_at?: string
  result_path?: string
}

// 当前表单（简化版）
const currentExperiment = ref<ExperimentConfig>({
  name: '',
  random_seed: 42,
  use_rag: false,  // RAG知识检索
  use_expert_routing: true,  // 专家路由
  enable_iteration: true,  // 默认启用迭代
  max_questions: null,
  subject: null,
  year: null
})

// 实验队列
const experimentQueue = ref<ExperimentItem[]>([])
const experimentForms = ref<ExperimentConfig[]>([])

// 状态
const loading = ref(false)
const isStarting = ref(false)
const isStopping = ref(false)
const isExecuting = ref(false)
const currentRunningExperiment = ref<ExperimentItem | null>(null)
const availableSubjects = ref<string[]>([])

// 轮询定时器
let pollTimer: number | null = null
// 标记当前实验是否已处理完成，防止重复处理
let completedExperimentIds = new Set<string>()

// ============ 计算属性 ============

const queueStats = computed(() => {
  return {
    pending: experimentQueue.value.filter(e => e.status === 'pending').length,
    running: experimentQueue.value.filter(e => e.status === 'running').length,
    completed: experimentQueue.value.filter(e => e.status === 'completed').length
  }
})

const canStart = computed(() => {
  return experimentQueue.value.length > 0 && 
         queueStats.value.pending > 0 && 
         queueStats.value.running === 0
})

const hasCompletedExperiments = computed(() => {
  return experimentQueue.value.some(e => e.status === 'completed')
})

const statusHint = computed(() => {
  if (experimentQueue.value.length === 0) {
    return '请先添加至少一个实验组'
  }
  if (queueStats.value.running > 0) {
    return '已有实验正在执行中'
  }
  if (queueStats.value.pending === 0) {
    return '所有实验已完成'
  }
  return ''
})

// ============ 方法 ============

// 获取状态标签类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

// 获取状态显示文本
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

// 格式化时间
const formatTime = (isoString: string) => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 加载学科列表
const loadSubjects = async () => {
  try {
    const res: any = await expertApi.listSubjects()
    if (res.code === 200) {
      availableSubjects.value = (res.data || []).filter((s: any) => s && typeof s === 'string')
    }
  } catch (error) {
    console.error('加载学科列表失败:', error)
  }
}

// 加载队列 - 纯数据刷新，不触发 benchmark 启动（启动逻辑在 startNextExperiment 中）
const loadQueue = async () => {
  loading.value = true
  try {
    const res: any = await experimentApi.getQueue()
    if (res.queue) {
      const currentId = currentRunningExperiment.value?.id

      // 更新队列数据
      experimentQueue.value = res.queue

      // 如果当前有运行中的实验，同步其状态字段
      if (currentId && currentRunningExperiment.value) {
        const updatedRunning = experimentQueue.value.find(e => e.id === currentId)
        if (updatedRunning) {
          currentRunningExperiment.value.status = updatedRunning.status
          currentRunningExperiment.value.progress = updatedRunning.progress
        }
      }

      // 页面初次加载时：如果没有当前实验但队列中有 running 的，恢复状态
      if (!currentRunningExperiment.value && !pollTimer && !isExecuting.value) {
        const running = experimentQueue.value.find(e => e.status === 'running')
        if (running) {
          console.log(`[Experiment] loadQueue 恢复运行中实验: ${running.name}`)
          // 页面刷新恢复场景：benchmark 可能已在后端运行，只需恢复前端状态和轮询
          currentRunningExperiment.value = running
          isExecuting.value = true
          startPolling()
        }
      }
    }
  } catch (error) {
    console.error('加载队列失败:', error)
    ElMessage.error('加载队列失败')
  } finally {
    loading.value = false
  }
}

// 添加实验到队列
const addExperiment = async () => {
  if (!currentExperiment.value.name.trim()) {
    ElMessage.warning('请输入实验名称')
    return
  }

  const config: ExperimentConfig = {
    ...currentExperiment.value,
    max_questions: currentExperiment.value.max_questions || null,
    subject: currentExperiment.value.subject || null,
    year: currentExperiment.value.year || null
  }

  try {
    const res: any = await experimentApi.createExperiments({
      experiments: [config]
    })
    
    if (res.success) {
      ElMessage.success('实验已添加到队列')
      experimentForms.value.push({ ...config })
      await loadQueue()
      resetForm()
    }
  } catch (error) {
    console.error('添加实验失败:', error)
    ElMessage.error('添加实验失败')
  }
}

// 从队列中移除
const removeExperiment = async (index: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要从队列中移除该实验吗？',
      '确认移除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    experimentQueue.value.splice(index, 1)
    ElMessage.success('已移除')
  } catch {
    // 取消
  }
}

// 清空队列
const clearQueue = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有实验队列吗？',
      '确认清空',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    const res: any = await experimentApi.clearExperiments()
    if (res.success) {
      experimentQueue.value = []
      experimentForms.value = []
      ElMessage.success('队列已清空')
    }
  } catch {
    // 取消
  }
}

// 重置表单
const resetForm = () => {
  currentExperiment.value = {
    name: '',
    random_seed: 42,
    use_rag: false,
    use_expert_routing: true,
    enable_iteration: true,
    max_questions: null,
    subject: null,
    year: null
  }
}

// 开始实验队列 - 修复重复启动问题
const startExperiments = async () => {
  if (experimentQueue.value.length === 0) {
    ElMessage.warning('队列中没有实验')
    return
  }
  
  // 🔥 关键修复：检查是否已经在运行中
  if (isExecuting.value || currentRunningExperiment.value || pollTimer) {
    console.log('[Experiment] 实验已在运行中，跳过重复启动')
    return
  }

  isStarting.value = true
  try {
    // 1. 启动实验队列管理
    const res: any = await experimentApi.startExperiments()
    if (!res.success) {
      ElMessage.warning(res.message || '启动失败')
      isStarting.value = false
      return
    }

    isExecuting.value = true
    currentRunningExperiment.value = res.experiment
    ElMessage.success(`开始执行: ${res.experiment.name}`)
    
    // 2. 启动实际的基准测试
    await startBenchmarkTest(res.experiment)
    
    // 3. 开始轮询状态（只启动一次）
    if (!pollTimer) {
      startPolling()
    }
    
    await loadQueue()
  } catch (error) {
    console.error('启动实验失败:', error)
    ElMessage.error('启动实验失败')
    isExecuting.value = false
  } finally {
    isStarting.value = false
  }
}

// 一键运行全部6组实验（科学顺序）- 修复状态管理
const runAllExperiments = async () => {
  // 🔥 关键修复：检查队列和状态
  if (experimentQueue.value.length > 0) {
    ElMessage.warning('队列中已有实验，请先清空')
    return
  }
  
  if (isExecuting.value || currentRunningExperiment.value) {
    ElMessage.warning('已有实验在运行中')
    return
  }
  
  isStarting.value = true
  // 🔥 关键修复：清空已完成的实验记录
  completedExperimentIds.clear()
  
  try {
    // 科学顺序：Baseline → ExpertOnly → 3轮FullSystem迭代 → RAGOnly（最后测RAG独立贡献）
    const allExperiments: ExperimentConfig[] = [
      { name: '① Baseline基线（无路由无RAG）', random_seed: 42, use_rag: false, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: '② ExpertOnly测试（有路由无RAG）', random_seed: 42, use_rag: false, use_expert_routing: true, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: '③ FullSystem第1轮（建库）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '④ FullSystem第2轮（进化1）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑤ FullSystem第3轮（进化2）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑥ RAGOnly测试（有库后）', random_seed: 42, use_rag: true, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null }
    ]
    
    console.log('[Experiment] 一键添加全部6组实验')
    
    // 添加全部实验到队列
    const res: any = await experimentApi.createExperiments({
      experiments: allExperiments
    })
    
    if (!res.success) {
      ElMessage.error(res.message || '添加实验失败')
      isStarting.value = false
      return
    }
    
    ElMessage.success('已添加6组实验，即将自动顺序执行')
    await loadQueue()
    
    // 🔥 关键修复：延迟一下再启动，确保后端已准备好
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 自动开始执行
    await startExperiments()
    
  } catch (error: any) {
    console.error('[Experiment] 一键运行失败:', error)
    ElMessage.error(`一键运行失败: ${error.message || '未知错误'}`)
    isStarting.value = false
  }
}

// 启动基准测试
const startBenchmarkTest = async (experiment: ExperimentItem) => {
  try {
    console.log('[Experiment] 启动测试配置:', {
      routing: experiment.config.use_expert_routing,
      rag: experiment.config.use_rag,
      iteration: experiment.config.enable_iteration
    })
    await benchmarkApi.startTest({
      expert_id: null, // 自动路由
      mode: 'all',
      subject: experiment.config.subject,
      year: experiment.config.year,
      experiment_id: experiment.id,
      random_seed: experiment.config.random_seed,
      use_rag: experiment.config.use_rag,
      use_expert_routing: experiment.config.use_expert_routing,
      enable_iteration: experiment.config.enable_iteration,
      max_questions: experiment.config.max_questions
    })
  } catch (error) {
    console.error('启动基准测试失败:', error)
    throw error
  }
}

// 停止实验
const stopExperiments = async () => {
  try {
    isStopping.value = true
    await benchmarkApi.stopTest()
    ElMessage.info('已发送停止指令')
    
    // 停止轮询
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    
    isExecuting.value = false
    currentRunningExperiment.value = null
    
    setTimeout(() => {
      loadQueue()
    }, 1000)
  } catch (error) {
    console.error('停止实验失败:', error)
    ElMessage.error('停止实验失败')
  } finally {
    isStopping.value = false
  }
}

// 轮询状态 - 重写：用 experiment_id 防止跨实验误判
const startPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }

  // 防重入：轮询回调正在执行时跳过下一次
  let pollBusy = false

  pollTimer = window.setInterval(async () => {
    if (pollBusy) return
    pollBusy = true

    try {
      const currentExp = currentRunningExperiment.value
      if (!currentExp) {
        console.log('[Experiment] 轮询: 没有当前运行实验')
        return
      }

      if (completedExperimentIds.has(currentExp.id)) {
        return
      }

      // 1. 获取基准测试进度
      const progress: any = await benchmarkApi.getProgress()

      // 竞态检查：轮询期间实验已切换
      if (currentRunningExperiment.value?.id !== currentExp.id) {
        return
      }

      // 🔥 核心修复：用 experiment_id 判断进度是否属于当前实验
      // 如果后端返回的 experiment_id 与当前实验不匹配，说明是旧数据，跳过
      if (progress.experiment_id && progress.experiment_id !== currentExp.id) {
        console.log(`[Experiment] 轮询: 进度属于旧实验 ${progress.experiment_id}，当前是 ${currentExp.id}，跳过`)
        return
      }

      // 更新当前实验进度（防止 total=0 时 NaN）
      if (progress.total > 0) {
        currentExp.progress = Math.round((progress.current / progress.total) * 100)
        currentExp.current_question = progress.current
        currentExp.total_questions = progress.total
      }

      // 2. 检查是否完成 —— 只信任 status 字段，不再用 current>=total 推断
      const isCompleted = progress.status === 'completed'

      if (isCompleted) {
        console.log(`[Experiment] 实验完成: ${currentExp.name}, ${progress.current}/${progress.total}`)

        completedExperimentIds.add(currentExp.id)

        // 停止轮询
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }

        // 等后端 complete_experiment 处理完（它会把下一个实验设为 running）
        await new Promise(resolve => setTimeout(resolve, 3000))

        currentRunningExperiment.value = null

        // 🔥 核心修复：直接查队列并启动下一个，不依赖 loadQueue 的副作用
        await startNextExperiment()

      } else if (progress.status === 'stopped' || progress.status === 'error') {
        isExecuting.value = false
        currentRunningExperiment.value = null
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }
        await loadQueue()
      }
    } catch (error) {
      console.error('轮询状态失败:', error)
    } finally {
      pollBusy = false
    }
  }, 3000)  // 3秒间隔，给后端更多处理时间
}

// 🔥 新增：启动下一个实验（从完成回调中抽出，逻辑更清晰）
const startNextExperiment = async () => {
  try {
    // 刷新队列获取最新状态
    const res: any = await experimentApi.getQueue()
    if (!res.queue) {
      isExecuting.value = false
      return
    }
    experimentQueue.value = res.queue

    // 查找后端已标记为 running 的下一个实验
    const nextRunning = experimentQueue.value.find(e => e.status === 'running')

    if (nextRunning) {
      console.log(`[Experiment] 启动下一个实验: ${nextRunning.name}`)

      // 🔥 先重置 benchmark 状态，确保旧的 completed 状态被清除
      try {
        await benchmarkApi.resetTest()
        // 短暂等待重置生效
        await new Promise(resolve => setTimeout(resolve, 500))
      } catch (resetErr) {
        console.warn('[Experiment] 重置 benchmark 状态失败（可忽略）:', resetErr)
      }

      // 启动新的 benchmark 测试
      await startBenchmarkTest(nextRunning)

      currentRunningExperiment.value = nextRunning
      isExecuting.value = true
      ElMessage.success(`开始实验: ${nextRunning.name}`)

      // 🔥 等待后端任务真正开始（第一道题开始处理），再启动轮询
      await new Promise(resolve => setTimeout(resolve, 2000))
      startPolling()
    } else {
      // 没有 running 的了，检查是否还有 pending
      const nextPending = experimentQueue.value.find(e => e.status === 'pending')
      if (nextPending) {
        // 后端没有自动推进，手动推进
        console.log(`[Experiment] 手动推进 pending 实验: ${nextPending.name}`)
        const startRes: any = await experimentApi.startExperiments()
        if (startRes.success && startRes.experiment) {
          await startBenchmarkTest(startRes.experiment)
          currentRunningExperiment.value = startRes.experiment
          isExecuting.value = true
          ElMessage.success(`开始实验: ${startRes.experiment.name}`)
          await new Promise(resolve => setTimeout(resolve, 2000))
          startPolling()
          await loadQueue()
        } else {
          isExecuting.value = false
        }
      } else {
        // 全部完成
        isExecuting.value = false
        completedExperimentIds.clear()
        ElMessage.success('所有实验已完成！')
        setTimeout(() => goToResults(), 1500)
      }
    }
  } catch (error: any) {
    console.error('[Experiment] 启动下一个实验失败:', error)
    ElMessage.error(`启动下一个实验失败: ${error.message || '未知错误'}`)
    isExecuting.value = false
  }
}

// 跳转到结果页面
const goToResults = () => {
  router.push('/benchmark')
}

// 应用预设
const applyPreset = (presetType: string) => {
  // 简化版预设配置：只用 use_rag 和 use_expert_routing 两个开关
  const presets: Record<string, ExperimentConfig[]> = {
    // 📌 第一阶段：消融实验（无RAG）- 禁用迭代
    phase1_baseline_expert: [
      { name: '① Baseline基线（无路由无RAG）', random_seed: 42, use_rag: false, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: '③ ExpertOnly测试（有路由无RAG）', random_seed: 42, use_rag: false, use_expert_routing: true, enable_iteration: false, max_questions: 50, subject: null, year: null }
    ],
    // 📌 第二阶段：先建库（3轮FullSystem迭代），最后测RAGOnly
    phase2_rag_fullsystem: [
      { name: '④ FullSystem第1轮（建库）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑤ FullSystem第2轮（进化1）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑥ FullSystem第3轮（进化2）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '② RAGOnly测试（有库后）', random_seed: 42, use_rag: true, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null }
    ],
    // RAG对比实验
    rag_comparison: [
      { name: 'RAG关闭', random_seed: 42, use_rag: false, use_expert_routing: true, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: 'RAG开启', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: false, max_questions: 50, subject: null, year: null }
    ],
    // 消融实验完整版（科学顺序：Baseline→ExpertOnly→3轮FullSystem建库→RAGOnly测试）
    full_ablation: [
      { name: '① Baseline基线', random_seed: 42, use_rag: false, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: '② ExpertOnly测试', random_seed: 42, use_rag: false, use_expert_routing: true, enable_iteration: false, max_questions: 50, subject: null, year: null },
      { name: '③ FullSystem第1轮（建库）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '④ FullSystem第2轮（进化1）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑤ FullSystem第3轮（进化2）', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '⑥ RAGOnly测试（有库后）', random_seed: 42, use_rag: true, use_expert_routing: false, enable_iteration: false, max_questions: 50, subject: null, year: null }
    ],
    // 种子鲁棒性测试
    seed_robustness: [
      { name: '种子=42', random_seed: 42, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '种子=123', random_seed: 123, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '种子=456', random_seed: 456, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null },
      { name: '种子=789', random_seed: 789, use_rag: true, use_expert_routing: true, enable_iteration: true, max_questions: 50, subject: null, year: null }
    ]
  }

  const presetConfigs = presets[presetType]
  if (!presetConfigs) return

  ElMessageBox.confirm(
    `将添加 ${presetConfigs.length} 组实验到队列，确定吗？`,
    '应用预设',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
  ).then(async () => {
    try {
      const res: any = await experimentApi.createExperiments({
        experiments: presetConfigs
      })
      if (res.success) {
        ElMessage.success(`已添加 ${presetConfigs.length} 组实验`)
        experimentForms.value.push(...presetConfigs)
        await loadQueue()
      }
    } catch (error) {
      console.error('添加预设失败:', error)
      ElMessage.error('添加预设失败')
    }
  }).catch(() => {})
}

// ============ 生命周期 ============

onMounted(() => {
  loadSubjects()
  loadQueue()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped lang="scss">
// 确保页面可以滚动
:global(html), :global(body) {
  overflow-x: hidden !important;
  overflow-y: auto !important;
  height: auto !important;
}

// 全局覆盖：确保所有卡片和表格无高度限制
:deep(.el-card) {
  height: auto !important;
  max-height: none !important;
  overflow-x: hidden !important;
  overflow-y: visible !important;
}

:deep(.el-card__body) {
  height: auto !important;
  max-height: none !important;
  overflow-x: hidden !important;
  overflow-y: visible !important;
}

.experiments-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100vh;
  height: auto;
  width: 100%;
  max-width: 100%;
  padding: 16px 24px;
  overflow-x: hidden;
  overflow-y: visible;
  box-sizing: border-box;
}

.page-header {
  background: linear-gradient(135deg, #5C63A9 0%, #4CC9BB 100%);
  border: 3px solid #111;
  box-shadow: 6px 6px 0 0 #111;
  padding: 20px 28px;
  color: white;

  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    h1 {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 28px;
      font-weight: 700;
      margin: 0;
    }
  }

  .header-desc {
    margin: 0;
    opacity: 0.9;
    font-size: 14px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 16px;

  span {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .count-tag {
    margin-left: 8px;
  }
}

.create-card {
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;
  
  :deep(.el-card__body) {
    padding: 20px 24px;
  }
}

.experiment-form {
  :deep(.el-form-item__label) {
    font-size: 14px;
    font-weight: 600;
    padding-bottom: 4px;
  }

  .el-form-item {
    margin-bottom: 16px;
  }

  .form-hint {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: #666;
  }

  .switch-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 14px;
  }
}

.queue-card {
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    padding: 20px;
    display: flex;
    flex-direction: column;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.queue-table {
  width: 100%;
  
  :deep(.el-table) {
    height: auto !important;
    max-height: none !important;
  }
  
  :deep(.el-table__inner-wrapper) {
    height: auto !important;
    max-height: none !important;
  }
  
  :deep(.el-table__header-wrapper) {
    height: auto !important;
  }
  
  :deep(.el-table__body-wrapper) {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
  }
  
  :deep(.el-table__cell) {
    padding: 14px 0;
  }

  .experiment-name {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 600;
    font-size: 15px;

    .el-icon {
      color: #5C63A9;
      font-size: 18px;
    }
  }

  .config-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
}

// 实验流程样式
.experiment-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin: 12px 0;
}

.flow-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 2px solid #e9ecef;
}

.step-num {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #5C63A9, #4CC9BB);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-content strong {
  color: #333;
  font-size: 15px;
}

.step-detail {
  margin-top: 4px;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.step-note {
  color: #5C63A9;
  font-weight: 500;
}

.flow-arrow {
  text-align: center;
  color: #999;
  font-size: 14px;
  margin: -6px 0;
}

.control-section {
  .control-card {
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    
    :deep(.el-card__body) {
      padding: 20px 24px;
    }
  }

  .control-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }

  .control-left,
  .control-right {
    display: flex;
    gap: 12px;
  }

  .executing-alert {
    margin-top: 16px;

    .progress-detail {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      font-size: 14px;

      .progress-percent {
        font-weight: 700;
        font-size: 16px;
      }
    }
  }

  .status-hint {
    margin-top: 16px;
  }
}

.preset-card {
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;

  :deep(.el-card__body) {
    padding: 20px 24px;
  }

  .preset-section {
    margin-bottom: 16px;

    .preset-title {
      font-weight: 600;
      font-size: 15px;
      margin-bottom: 12px;
      color: #333;
    }

    .preset-hint {
      margin-top: 12px;
      padding: 10px 14px;
      background: #f5f7fa;
      border-left: 4px solid #409eff;
      font-size: 13px;
      color: #666;
      line-height: 1.6;
    }
  }

  .preset-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;

    .el-button {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 12px 20px;
      font-size: 14px;
    }
  }
}

@media (max-width: 768px) {
  .control-content {
    flex-direction: column;
    align-items: stretch !important;

    .control-left,
    .control-right {
      justify-content: center;
    }
  }

  .preset-buttons {
    flex-direction: column;

    .el-button {
      width: 100%;
    }
  }
}
</style>
