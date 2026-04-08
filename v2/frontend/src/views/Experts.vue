<template>
  <div class="experts-page">
    <div class="experts-container">
      <!-- 顶部装饰条 -->
      <div class="experts-header-decor">
        <div class="window-dot pink"></div>
        <div class="window-dot yellow"></div>
        <div class="window-dot teal"></div>
        <span class="header-title">专家池管理 Expert Pool</span>
      </div>
      
      <div class="experts-content">
        <div class="page-header">
          <h1 class="page-title">🎓 专家池管理 Experts</h1>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            添加学科专家
          </el-button>
        </div>

        <!-- 学科筛选标签 -->
        <div class="subject-tabs">
          <div 
            v-for="subject in allSubjects" 
            :key="subject.subject"
            :class="['subject-tab', { active: subject.has_expert, selected: selectedSubject === subject.subject }]"
            @click="selectSubject(subject.subject)"
          >
            <span class="subject-name">{{ subject.subject }}</span>
            <span v-if="subject.has_expert" class="status-dot active"></span>
            <span v-else class="status-dot inactive"></span>
          </div>
        </div>

        <!-- 统计概览 -->
        <div class="stats-bar">
          <div class="stat-item">
            <span class="stat-value">{{ experts.length }}</span>
            <span class="stat-label">已启用学科</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ allSubjects.length - experts.length }}</span>
            <span class="stat-label">待添加学科</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ totalKnowledge }}</span>
            <span class="stat-label">总知识条目</span>
          </div>
        </div>

        <!-- 专家列表 -->
        <div v-if="filteredExperts.length > 0" class="experts-grid">
          <el-card v-for="expert in filteredExperts" :key="expert.id" class="expert-card">
            <div class="expert-header">
              <div class="expert-avatar" :style="{ background: getAvatarColor(expert.subject) }">
                {{ expert.subject[0] }}
              </div>
              <div class="expert-info">
                <h3>{{ expert.name }}</h3>
                <div class="expert-tags">
                  <el-tag v-if="!expert.is_active" type="danger" size="small" effect="light">已禁用</el-tag>
                </div>
              </div>
            </div>

            <div class="expert-stats">
              <div class="stat-row">
                <span>📚 知识库</span>
                <strong>{{ expert.knowledge_count }}</strong>
              </div>
              <div class="stat-row">
                <span>🤖 微调数据</span>
                <strong>{{ expert.sft_data_count }}</strong>
              </div>
              <div class="stat-row">
                <span>💬 问答次数</span>
                <strong>{{ expert.total_qa_count }}</strong>
              </div>
              <div class="stat-row">
                <span>⏱️ 平均响应</span>
                <strong>{{ expert.avg_response_time.toFixed(0) }}ms</strong>
              </div>
              <div class="stat-row">
                <span>🎯 准确率</span>
                <strong>{{ (expert.accuracy_rate * 100).toFixed(1) }}%</strong>
              </div>
            </div>

            <div class="expert-actions">
              <el-button type="primary" text @click="viewExpertDetail(expert)">
                查看详情
              </el-button>
            </div>
          </el-card>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-empty description="该学科专家尚未创建">
            <el-button type="primary" @click="showCreateDialog = true">
              立即创建
            </el-button>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- 创建专家对话框 -->
    <el-dialog v-model="showCreateDialog" title="添加学科专家" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="学科">
          <el-select v-model="createForm.subject" placeholder="选择学科">
            <el-option 
              v-for="s in availableSubjects" 
              :key="s.subject" 
              :label="s.subject" 
              :value="s.subject" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="createForm.name" placeholder="如：数学专家（可选，默认自动生成）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createExpert" :loading="isCreating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 专家详情弹窗 -->
    <el-dialog 
      v-model="showDetailDialog" 
      :title="currentExpert ? `${currentExpert.name} 详情` : '专家详情'" 
      width="900px"
      class="expert-detail-dialog"
    >
      <div v-if="currentExpert" class="expert-detail">
        <!-- 统计概览卡片 -->
        <div class="stats-overview">
          <div class="stat-card">
            <div class="stat-icon">📚</div>
            <div class="stat-info">
              <div class="stat-value">{{ knowledgeStats.total_knowledge || 0 }}</div>
              <div class="stat-label">知识库总量</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">⭐</div>
            <div class="stat-info">
              <div class="stat-value">{{ knowledgeStats.quality_distribution?.high || 0 }}</div>
              <div class="stat-label">高质量知识</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💬</div>
            <div class="stat-info">
              <div class="stat-value">{{ currentExpert.total_qa_count }}</div>
              <div class="stat-label">问答次数</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">⏱️</div>
            <div class="stat-info">
              <div class="stat-value">{{ currentExpert.avg_response_time.toFixed(0) }}ms</div>
              <div class="stat-label">平均响应</div>
            </div>
          </div>
        </div>

        <!-- 知识类型分布 -->
        <div v-if="knowledgeStats.type_distribution" class="type-distribution">
          <h4>📊 知识类型分布</h4>
          <div class="type-bars">
            <div 
              v-for="(label, type) in typeLabels" 
              :key="type"
              class="type-bar-item"
              :class="{ active: filterType === type }"
              @click="filterType = filterType === type ? null : type"
            >
              <div class="type-label">{{ label }}</div>
              <div class="type-bar">
                <div 
                  class="type-fill" 
                  :style="{ width: getTypePercentage(type) + '%', background: typeColors[type] }"
                ></div>
              </div>
              <div class="type-count">{{ knowledgeStats.type_distribution?.[type] || 0 }}</div>
            </div>
          </div>
        </div>

        <!-- 来源分布 -->
        <div v-if="knowledgeStats.source_distribution" class="source-distribution">
          <h4>📥 知识来源分布</h4>
          <div class="source-tags">
            <el-tag 
              v-for="(label, source) in sourceLabels" 
              :key="source"
              :type="sourceTypeMap[source]"
              effect="light"
              class="source-tag"
            >
              {{ label }}: {{ knowledgeStats.source_distribution[source] || 0 }}
            </el-tag>
          </div>
        </div>

        <!-- 知识列表筛选 -->
        <div class="knowledge-filter">
          <h4>🔍 知识库列表</h4>
          <div class="filter-bar">
            <el-select v-model="filterType" placeholder="全部类型" clearable size="small">
              <el-option 
                v-for="(label, type) in typeLabels" 
                :key="type" 
                :label="label" 
                :value="type" 
              />
            </el-select>
            <el-select v-model="filterSource" placeholder="全部来源" clearable size="small">
              <el-option 
                v-for="(label, source) in sourceLabels" 
                :key="source" 
                :label="label" 
                :value="source" 
              />
            </el-select>
            <el-select v-model="filterQuality" placeholder="全部质量" clearable size="small">
              <el-option label="高质量 (≥4.0)" value="high" />
              <el-option label="中等 (3.0-4.0)" value="medium" />
              <el-option label="低质量 (<3.0)" value="low" />
            </el-select>
            <el-button type="primary" size="small" @click="loadKnowledgeList" :loading="knowledgeLoading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>

        <!-- 知识列表 -->
        <div class="knowledge-list" v-loading="knowledgeLoading">
          <div v-if="knowledgeList.length === 0" class="empty-knowledge">
            <el-empty description="暂无知识数据" :image-size="80" />
          </div>
          <div 
            v-for="item in knowledgeList" 
            :key="item.id" 
            class="knowledge-item"
          >
            <div class="knowledge-header">
              <div class="knowledge-tags">
                <el-tag :color="typeColors[item.knowledge_type]" effect="light" size="small">
                  {{ typeLabels[item.knowledge_type] }}
                </el-tag>
                <el-tag :type="sourceTypeMap[item.source_type]" effect="light" size="small">
                  {{ sourceLabels[item.source_type] }}
                </el-tag>
                <el-tag 
                  :type="item.quality_score >= 4 ? 'success' : item.quality_score >= 3 ? 'warning' : 'danger'" 
                  effect="light" 
                  size="small"
                >
                  综合: {{ item.quality_score?.toFixed(2) }}
                </el-tag>
              </div>
              <!-- 多维度质量评分 -->
              <div v-if="item.accuracy_score" class="quality-dimensions">
                <el-tooltip content="准确性" placement="top">
                  <span class="dim-tag accuracy">🎯 {{ item.accuracy_score?.toFixed(1) }}</span>
                </el-tooltip>
                <el-tooltip content="完整性" placement="top">
                  <span class="dim-tag completeness">📊 {{ item.completeness_score?.toFixed(1) }}</span>
                </el-tooltip>
                <el-tooltip content="教育性" placement="top">
                  <span class="dim-tag educational">📚 {{ item.educational_score?.toFixed(1) }}</span>
                </el-tooltip>
                <el-tooltip v-if="item.additional_score" :content="getAdditionalDimName(item.knowledge_type)" placement="top">
                  <span class="dim-tag additional">⭐ {{ item.additional_score?.toFixed(1) }}</span>
                </el-tooltip>
              </div>
              <span class="knowledge-date">{{ formatDate(item.created_at) }}</span>
            </div>
            <div class="knowledge-content">
              <div v-if="item.meta_data?.question" class="knowledge-question">
                <strong>问题：</strong>{{ item.meta_data.question }}
              </div>
              <div v-else class="knowledge-question">
                {{ item.content }}
              </div>
              <div v-if="item.meta_data?.answer" class="knowledge-answer">
                <strong>答案：</strong>{{ item.meta_data.answer.substring(0, 200) }}
                <span v-if="item.meta_data.answer.length > 200">...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination" v-if="knowledgeTotal > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="knowledgeTotal"
            layout="prev, pager, next, sizes"
            :page-sizes="[5, 10, 20]"
            @change="loadKnowledgeList"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { expertApi } from '../api'

interface Expert {
  id: number
  name: string
  subject: string
  knowledge_count: number
  sft_data_count: number
  total_qa_count: number
  avg_response_time: number
  accuracy_rate: number
  is_active: boolean
  model_type?: string
}

interface SubjectInfo {
  subject: string
  has_expert: boolean
  expert_id: number | null
  is_default: boolean
}

interface KnowledgeItem {
  id: number
  content: string
  knowledge_type: string
  source_type: string
  quality_score: number
  accuracy_score?: number      // 准确性
  completeness_score?: number  // 完整性
  educational_score?: number   // 教育性
  additional_score?: number    // 额外维度
  usage_count: number
  meta_data: any
  created_at: string
}

const experts = ref<Expert[]>([])
const allSubjects = ref<SubjectInfo[]>([])
const selectedSubject = ref<string>('')
const showCreateDialog = ref(false)
const isCreating = ref(false)
const createForm = ref({ subject: '', name: '' })

// 详情弹窗相关
const showDetailDialog = ref(false)
const currentExpert = ref<Expert | null>(null)
const knowledgeStats = ref<any>({})
const knowledgeList = ref<KnowledgeItem[]>([])
const knowledgeLoading = ref(false)
const knowledgeTotal = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

// 筛选条件
const filterType = ref<string | null>(null)
const filterSource = ref<string | null>(null)
const filterQuality = ref<string | null>(null)

// 类型标签和颜色
const typeLabels: Record<string, string> = {
  qa: '问答对',
  concept: '核心概念',
  formula: '公式/定律',
  template: '解题模板',
  step: '步骤/方法'
}

const typeColors: Record<string, string> = {
  qa: '#FF78A5',
  concept: '#4CC9BB',
  formula: '#FFF14F',
  template: '#F28E70',
  step: '#5C63A9'
}

const sourceLabels: Record<string, string> = {
  generated: '云端生成',
  wrong_answer_extracted: '错题挖掘',
  manual: '手动添加'
}

const sourceTypeMap: Record<string, string> = {
  generated: 'success',
  wrong_answer_extracted: 'warning',
  manual: 'info'
}

const filteredExperts = computed(() => {
  if (selectedSubject.value) {
    return experts.value.filter(e => e.subject === selectedSubject.value)
  }
  return experts.value
})

const totalKnowledge = computed(() => experts.value.reduce((sum, e) => sum + e.knowledge_count, 0))

const availableSubjects = computed(() => 
  allSubjects.value.filter(s => !s.has_expert)
)

const subjectColors: Record<string, string> = {
  '数学': '#FF78A5',
  '物理': '#4CC9BB',
  '化学': '#FFF14F',
  '语文': '#F28E70',
  '英语': '#5C63A9',
  '生物': '#4CC9BB',
  '历史': '#C77DFF',
  '地理': '#7FD8BE',
  '政治': '#FFB703',
  '其他': '#999'
}

function getAvatarColor(subject: string): string {
  return subjectColors[subject] || '#999'
}

function selectSubject(subject: string) {
  selectedSubject.value = selectedSubject.value === subject ? '' : subject
}

function getTypePercentage(type: string): number {
  const total = knowledgeStats.value?.total_knowledge || 0
  const count = knowledgeStats.value?.type_distribution?.[type] || 0
  return total > 0 ? Math.round((count / total) * 100) : 0
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// 查看专家详情
async function viewExpertDetail(expert: Expert) {
  currentExpert.value = expert
  showDetailDialog.value = true
  
  // 加载统计数据
  try {
    const statsRes: any = await expertApi.getKnowledgeStats(expert.id)
    if (statsRes.code === 200) {
      knowledgeStats.value = statsRes.data
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
  
  // 加载知识列表
  await loadKnowledgeList()
}

// 加载知识列表
async function loadKnowledgeList() {
  if (!currentExpert.value) return
  
  knowledgeLoading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (filterType.value) params.knowledge_type = filterType.value
    if (filterSource.value) params.source_type = filterSource.value
    if (filterQuality.value) {
      const qualityMap: Record<string, number> = { high: 4, medium: 3, low: 0 }
      params.min_quality = qualityMap[filterQuality.value] || 0
    }
    
    const res: any = await expertApi.getKnowledgeList(currentExpert.value.id, params)
    if (res.code === 200) {
      knowledgeList.value = res.data.items
      knowledgeTotal.value = res.data.total
    }
  } catch (error) {
    console.error('加载知识列表失败:', error)
    ElMessage.error('加载知识列表失败')
  } finally {
    knowledgeLoading.value = false
  }
}

// 监听筛选条件变化
watch([filterType, filterSource, filterQuality], () => {
  currentPage.value = 1
  loadKnowledgeList()
})

async function loadExperts() {
  const res: any = await expertApi.list()
  if (res.code === 200) {
    experts.value = res.data
  }
}

async function loadSubjects() {
  try {
    const res: any = await expertApi.listSubjects()
    if (res.code === 200) {
      allSubjects.value = res.data
    }
  } catch (e) {
    buildSubjectsFromExperts()
  }
}

function buildSubjectsFromExperts() {
  const defaultSubjects = ["数学", "物理", "化学", "语文", "英语", "生物", "历史", "地理", "政治", "通用"]
  const expertMap = new Map(experts.value.map(e => [e.subject, e.id]))
  
  allSubjects.value = defaultSubjects.map(subject => ({
    subject,
    has_expert: expertMap.has(subject),
    expert_id: expertMap.get(subject) || null,
    is_default: true
  }))
}

// 根据知识类型获取额外维度名称
function getAdditionalDimName(knowledgeType: string): string {
  const dimNames: Record<string, string> = {
    qa: '回答质量',
    concept: '深度理解',
    formula: '规范表达',
    template: '复用性',
    step: '逻辑清晰'
  }
  return dimNames[knowledgeType] || '额外维度'
}

async function createExpert() {
  if (!createForm.value.subject) {
    ElMessage.warning('请选择学科')
    return
  }
  
  isCreating.value = true
  try {
    const res: any = await expertApi.create({
      subject: createForm.value.subject,
      name: createForm.value.name || undefined
    })
    
    if (res.code === 200) {
      ElMessage.success('学科专家创建成功')
      showCreateDialog.value = false
      createForm.value = { subject: '', name: '' }
      await loadExperts()
      await loadSubjects()
    }
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    isCreating.value = false
  }
}

onMounted(() => {
  loadExperts()
  loadSubjects()
})
</script>

<style scoped lang="scss">
.experts-page {
  width: 100%;
  height: 100%;
  background: #f5f5f5;
  overflow-y: auto;
}

.experts-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.experts-header-decor {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: white;
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;
  
  .window-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #111;
    
    &.pink { background: #FF78A5; }
    &.yellow { background: #FFF14F; }
    &.teal { background: #4CC9BB; }
  }
  
  .header-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 14px;
    margin-left: 8px;
  }
}

.experts-content {
  background: white;
  border: 3px solid #111;
  box-shadow: 6px 6px 0 0 #111;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  .page-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 24px;
    font-weight: 700;
    margin: 0;
  }
}

.subject-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
  
  .subject-tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: #f5f5f5;
    border: 2px solid #ddd;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      transform: translate(-2px, -2px);
      box-shadow: 2px 2px 0 0 #111;
    }
    
    &.active {
      background: #E8F5E9;
      border-color: #2E7D32;
    }
    
    &.selected {
      background: #FFF14F;
      border-color: #111;
      box-shadow: 3px 3px 0 0 #111;
    }
    
    .subject-name {
      font-weight: 600;
    }
    
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      
      &.active { background: #2E7D32; }
      &.inactive { background: #ccc; }
    }
  }
}

.stats-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f9f9f9;
  border: 2px solid #eee;
  
  .stat-item {
    flex: 1;
    text-align: center;
    
    .stat-value {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 28px;
      font-weight: 700;
      color: #111;
    }
    
    .stat-label {
      font-size: 12px;
      color: #666;
      margin-top: 4px;
    }
  }
}

.experts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.expert-card {
  :deep(.el-card__body) {
    padding: 16px;
  }
  
  .expert-header {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    
    .expert-avatar {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
      color: white;
      border: 2px solid #111;
    }
    
    .expert-info {
      h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 16px;
        margin: 0 0 4px 0;
      }
      
      .expert-tags {
        display: flex;
        gap: 4px;
      }
    }
  }
  
  .expert-stats {
    .stat-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #eee;
      
      &:last-child {
        border-bottom: none;
      }
      
      span {
        color: #666;
        font-size: 13px;
      }
      
      strong {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 14px;
      }
    }
  }
  
  .expert-actions {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 2px solid #eee;
    display: flex;
    justify-content: center;
  }
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

// 详情弹窗样式
.expert-detail-dialog {
  :deep(.el-dialog__body) {
    max-height: 70vh;
    overflow-y: auto;
    padding: 20px;
  }
}

.expert-detail {
  .stats-overview {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
    
    .stat-card {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      background: #f9f9f9;
      border: 2px solid #eee;
      border-radius: 8px;
      
      .stat-icon {
        font-size: 28px;
      }
      
      .stat-info {
        .stat-value {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 24px;
          font-weight: 700;
        }
        
        .stat-label {
          font-size: 12px;
          color: #666;
        }
      }
    }
  }
  
  .type-distribution,
  .source-distribution {
    margin-bottom: 24px;
    padding: 16px;
    background: #f9f9f9;
    border: 2px solid #eee;
    border-radius: 8px;
    
    h4 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 16px 0;
      font-size: 14px;
    }
  }
  
  .type-bars {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    .type-bar-item {
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      transition: background 0.2s;
      
      &:hover,
      &.active {
        background: #e3f2fd;
      }
      
      .type-label {
        width: 80px;
        font-size: 13px;
        font-weight: 500;
      }
      
      .type-bar {
        flex: 1;
        height: 20px;
        background: #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
        
        .type-fill {
          height: 100%;
          transition: width 0.3s;
        }
      }
      
      .type-count {
        width: 40px;
        text-align: right;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
      }
    }
  }
  
  .source-tags {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    
    .source-tag {
      font-size: 13px;
    }
  }
  
  .knowledge-filter {
    margin-bottom: 16px;
    
    h4 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0 0 12px 0;
      font-size: 14px;
    }
    
    .filter-bar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
  }
  
  .knowledge-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 400px;
    overflow-y: auto;
    
    .empty-knowledge {
      padding: 40px 0;
    }
    
    .knowledge-item {
      padding: 16px;
      background: white;
      border: 2px solid #eee;
      border-radius: 8px;
      
      &:hover {
        border-color: #4CC9BB;
      }
      
      .knowledge-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        
        .knowledge-tags {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        
        .quality-dimensions {
          display: flex;
          gap: 8px;
          margin-top: 8px;
          
          .dim-tag {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            
            &.accuracy {
              background: #E3F2FD;
              color: #1565C0;
            }
            
            &.completeness {
              background: #F3E5F5;
              color: #7B1FA2;
            }
            
            &.educational {
              background: #E8F5E9;
              color: #2E7D32;
            }
            
            &.additional {
              background: #FFF8E1;
              color: #F57C00;
            }
          }
        }
        
        .knowledge-date {
          font-size: 12px;
          color: #999;
        }
      }
      
      .knowledge-content {
        .knowledge-question {
          font-size: 14px;
          color: #333;
          margin-bottom: 8px;
          
          strong {
            color: #1565C0;
          }
        }
        
        .knowledge-answer {
          font-size: 13px;
          color: #666;
          line-height: 1.6;
          
          strong {
            color: #2E7D32;
          }
        }
      }
    }
  }
  
  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .experts-grid {
    grid-template-columns: 1fr;
  }
  
  .expert-detail {
    .stats-overview {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
</style>
