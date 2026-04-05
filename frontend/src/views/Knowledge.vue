<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h1 class="page-title">📚 知识库管理 Knowledge Base</h1>
      <div class="header-stats">
        <el-tag type="primary" effect="light">总计: {{ total }} 条</el-tag>
        <el-tag type="success" effect="light" v-if="avgQuality">平均质量: {{ avgQuality.toFixed(2) }}</el-tag>
      </div>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加知识
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filterExpert" placeholder="选择专家" clearable style="width: 160px">
        <el-option
          v-for="expert in experts"
          :key="expert.id"
          :label="expert.name"
          :value="expert.id"
        />
      </el-select>
      <el-select v-model="filterSource" placeholder="来源类型" clearable style="width: 160px">
        <el-option label="云端质检" value="generated" />
        <el-option label="错题挖掘" value="wrong_answer_extracted" />
        <el-option label="手动添加" value="manual" />
      </el-select>
      <el-select v-model="filterQuality" placeholder="质量筛选" clearable style="width: 140px">
        <el-option label="高质量 (>=4.0)" value="high" />
        <el-option label="中等 (3.0-4.0)" value="medium" />
        <el-option label="低质量 (<3.0)" value="low" />
      </el-select>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索知识点..."
        style="width: 250px"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" plain @click="loadKnowledge" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 知识列表 -->
    <el-table 
      :data="knowledge" 
      border 
      stripe 
      v-loading="loading" 
      @filter-change="handleFilterChange"
      height="600"
      style="width: 100%"
    >
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column 
        prop="expert_name" 
        label="所属专家" 
        width="120"
        :filters="expertFilters"
        :filter-method="filterExpertHandler"
        filter-placement="bottom"
      >
        <template #default="{ row }">
          <el-tag size="small" :color="getSubjectColor(row.expert_id)" style="color: #fff; border: none;">
            {{ row.expert_name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="知识内容" min-width="400">
        <template #default="{ row }">
          <div class="knowledge-item">
            <div class="knowledge-question" v-if="parseContent(row.content).question">
              <strong>问题：</strong>{{ parseContent(row.content).question }}
            </div>
            <div class="knowledge-answer" v-if="parseContent(row.content).answer">
              <strong>答案：</strong>{{ parseContent(row.content).answer }}
            </div>
            <div class="knowledge-raw" v-else>{{ row.content }}</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column 
        prop="source_type" 
        label="来源" 
        width="120"
        :filters="[
          { text: '云端质检', value: 'generated' },
          { text: '错题挖掘', value: 'wrong_answer_extracted' },
          { text: '手动添加', value: 'manual' }
        ]"
        :filter-method="filterSourceHandler"
      >
        <template #default="{ row }">
          <el-tag :type="getSourceType(row.source_type)" size="small" effect="light">
            {{ getSourceLabel(row.source_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column 
        prop="quality_score" 
        label="质量分" 
        width="100"
        :filters="[
          { text: '≥4.0', value: 'high' },
          { text: '3.0-4.0', value: 'medium' },
          { text: '<3.0', value: 'low' }
        ]"
        :filter-method="filterQualityHandler"
      >
        <template #default="{ row }">
          <el-tag 
            :type="row.quality_score >= 4 ? 'success' : row.quality_score >= 3 ? 'warning' : 'danger'" 
            size="small" 
            effect="light"
          >
            {{ row.quality_score.toFixed ? row.quality_score.toFixed(2) : row.quality_score }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="usage_count" label="引用次数" width="90" sortable />
      <el-table-column prop="created_at" label="创建时间" width="160" sortable>
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewDetail(row)">
            详情
          </el-button>
          <el-button type="danger" link size="small" @click="deleteKnowledge(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadKnowledge"
        @size-change="loadKnowledge"
      />
    </div>

    <!-- 添加知识对话框 -->
    <el-dialog v-model="showAddDialog" title="添加知识点" width="600px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="所属专家" required>
          <el-select v-model="addForm.expert_id" placeholder="选择专家">
            <el-option
              v-for="expert in experts"
              :key="expert.id"
              :label="expert.name"
              :value="expert.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="知识内容" required>
          <el-input
            v-model="addForm.content"
            type="textarea"
            :rows="5"
            placeholder="输入知识点内容..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addKnowledge" :loading="isAdding">
          添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="知识详情" width="700px">
      <div v-if="currentKnowledge" class="knowledge-detail">
        <div class="detail-row">
          <span class="label">专家:</span>
          <el-tag size="small" :color="getSubjectColor(currentKnowledge.expert_id)" style="color: #fff; border: none;">
            {{ currentKnowledge.expert_name }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="label">来源:</span>
          <el-tag :type="getSourceType(currentKnowledge.source_type)" size="small" effect="light">
            {{ getSourceLabel(currentKnowledge.source_type) }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="label">质量分:</span>
          <el-tag :type="currentKnowledge.quality_score >= 4 ? 'success' : currentKnowledge.quality_score >= 3 ? 'warning' : 'danger'" size="small" effect="light">
            {{ currentKnowledge.quality_score }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="label">引用次数:</span>
          <span>{{ currentKnowledge.usage_count }}</span>
        </div>
        <div class="detail-row">
          <span class="label">创建时间:</span>
          <span>{{ formatDate(currentKnowledge.created_at) }}</span>
        </div>
        <div class="detail-content">
          <!-- 问题 -->
          <div v-if="currentKnowledge.question" class="content-section">
            <div class="content-label">问题：</div>
            <pre class="content-text question-text">{{ currentKnowledge.question }}</pre>
          </div>
          
          <!-- 答案 -->
          <div class="content-section">
            <div class="content-label">答案：</div>
            <pre class="content-text answer-text">{{ currentKnowledge.content }}</pre>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { expertApi, knowledgeApi } from '../api'

interface Knowledge {
  id: number
  content: string
  question?: string  // 问题
  expert_id: number
  expert_name: string
  source_type: string
  quality_score: number
  usage_count: number
  created_at: string
}

interface Expert {
  id: number
  name: string
  subject?: string
}

const knowledge = ref<Knowledge[]>([])
const experts = ref<Expert[]>([])
const filterExpert = ref('')
const filterSource = ref('')
const filterQuality = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const avgQuality = ref(0)
const showAddDialog = ref(false)
const isAdding = ref(false)
const addForm = ref({ expert_id: '', content: '' })
const detailVisible = ref(false)
const currentKnowledge = ref<Knowledge | null>(null)

// 专家颜色映射
const subjectColors: Record<string, string> = {
  '数学': '#2E7D32',
  '物理': '#1565C0',
  '化学': '#C62828',
  '生物': '#6A1B9A',
  '历史': '#5D4037',
  '地理': '#00695C',
  '政治': '#AD1457',
  '语文': '#F57F17',
  '英语': '#E65100',
  '通用': '#455A64'
}

// 专家筛选选项
const expertFilters = computed(() => {
  return experts.value.map(e => ({ text: e.name, value: e.id }))
})

// 监听筛选条件变化，自动刷新
watch([filterExpert, filterSource, filterQuality, searchKeyword], () => {
  currentPage.value = 1
  loadKnowledge()
}, { immediate: false })

async function loadExperts() {
  try {
    const res: any = await expertApi.list()
    if (res.code === 200) {
      experts.value = res.data.map((e: any) => ({ id: e.id, name: e.name, subject: e.subject }))
    }
  } catch (error) {
    console.error('加载专家列表失败:', error)
  }
}

async function loadKnowledge() {
  loading.value = true
  try {
    const res: any = await knowledgeApi.list({
      expert_id: filterExpert.value || undefined,
      keyword: searchKeyword.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (res.code === 200) {
      knowledge.value = res.data.items
      total.value = res.data.total
      // 客户端过滤
      if (filterSource.value) {
        knowledge.value = knowledge.value.filter((k: Knowledge) => k.source_type === filterSource.value)
      }
      if (filterQuality.value) {
        knowledge.value = knowledge.value.filter((k: Knowledge) => {
          if (filterQuality.value === 'high') return k.quality_score >= 4
          if (filterQuality.value === 'medium') return k.quality_score >= 3 && k.quality_score < 4
          if (filterQuality.value === 'low') return k.quality_score < 3
          return true
        })
      }
    }
    // 加载统计
    await loadStats()
  } catch (error) {
    console.error('加载知识列表失败:', error)
    ElMessage.error('加载知识列表失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const res: any = await knowledgeApi.getStats()
    if (res.code === 200) {
      avgQuality.value = res.data.avg_quality_score || 0
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

function getSubjectColor(expertId: number): string {
  const expert = experts.value.find(e => e.id === expertId)
  return subjectColors[expert?.subject || ''] || '#455A64'
}

function getSourceType(source: string): string {
  const map: Record<string, string> = {
    generated: 'success',
    wrong_answer_extracted: 'warning',
    manual: 'primary'
  }
  return map[source] || 'info'
}

function getSourceLabel(source: string): string {
  const map: Record<string, string> = {
    generated: '云端质检',
    wrong_answer_extracted: '错题挖掘',
    manual: '手动添加'
  }
  return map[source] || source
}

function parseContent(content: string) {
  // 解析知识内容，分离问题和答案
  const result = { question: '', answer: '' }
  
  // 匹配"问题："格式
  const questionMatch = content.match(/问题[:：]\s*(.+?)(?=\n|回答[:：]|$)/s)
  if (questionMatch) {
    result.question = questionMatch[1].trim()
  }
  
  // 匹配"回答："格式
  const answerMatch = content.match(/回答[:：]\s*(.+)/s)
  if (answerMatch) {
    result.answer = answerMatch[1].trim()
  }
  
  return result
}

function filterExpertHandler(value: number, row: Knowledge) {
  return row.expert_id === value
}

function filterSourceHandler(value: string, row: Knowledge) {
  return row.source_type === value
}

function filterQualityHandler(value: string, row: Knowledge) {
  if (value === 'high') return row.quality_score >= 4
  if (value === 'medium') return row.quality_score >= 3 && row.quality_score < 4
  if (value === 'low') return row.quality_score < 3
  return true
}

function handleFilterChange(filters: any) {
  // 处理列头筛选变化
  console.log('Filter changed:', filters)
}

function viewDetail(row: Knowledge) {
  currentKnowledge.value = row
  detailVisible.value = true
}

async function addKnowledge() {
  if (!addForm.value.expert_id || !addForm.value.content.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  isAdding.value = true
  try {
    const res: any = await knowledgeApi.create({
      expert_id: Number(addForm.value.expert_id),
      content: addForm.value.content,
      source_type: 'manual'
    })
    
    if (res.code === 200) {
      ElMessage.success('添加成功')
      showAddDialog.value = false
      addForm.value = { expert_id: '', content: '' }
      await loadKnowledge()
      // 刷新专家列表以更新知识计数
      await loadExperts()
    } else {
      ElMessage.error(res.message || '添加失败')
    }
  } catch (error) {
    console.error('添加知识失败:', error)
    ElMessage.error('添加失败')
  } finally {
    isAdding.value = false
  }
}

async function deleteKnowledge(row: Knowledge) {
  try {
    await ElMessageBox.confirm('确定删除该知识点吗？', '提示', { type: 'warning' })
    const res: any = await knowledgeApi.delete(row.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      await loadKnowledge()
      // 刷新专家列表以更新知识计数
      await loadExperts()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除知识失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadExperts()
  loadKnowledge()
})
</script>

<style scoped lang="scss">
// 强制修改 Element Plus Tag 颜色对比度
:deep(.el-tag--success) {
  background-color: #e6f7e6 !important;
  border-color: #2E7D32 !important;
  color: #1b5e20 !important;
}

:deep(.el-tag--warning) {
  background-color: #fff3e0 !important;
  border-color: #E65100 !important;
  color: #bf360c !important;
}

:deep(.el-tag--danger) {
  background-color: #ffebee !important;
  border-color: #C62828 !important;
  color: #b71c1c !important;
}

:deep(.el-tag--primary) {
  background-color: #e3f2fd !important;
  border-color: #1565C0 !important;
  color: #0d47a1 !important;
}

.knowledge-page {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  margin: 0;
  text-transform: uppercase;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  flex-wrap: wrap;
}

.knowledge-item {
  .knowledge-question {
    margin-bottom: 8px;
    color: #333;
    strong {
      color: #1565C0;
    }
  }
  .knowledge-answer {
    color: #666;
    font-size: 13px;
    strong {
      color: #2E7D32;
    }
  }
  .knowledge-raw {
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: #333;
  }
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

// 详情弹窗样式
.knowledge-detail {
  .detail-row {
    display: flex;
    margin-bottom: 12px;
    align-items: center;
    .label {
      width: 80px;
      color: #666;
      font-weight: 500;
    }
  }
  .detail-content {
    margin-top: 20px;
    border-top: 1px solid #eee;
    padding-top: 16px;
    
    .content-section {
      margin-bottom: 20px;
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    .content-label {
      font-weight: 600;
      margin-bottom: 8px;
      color: #333;
      font-size: 14px;
    }
    
    .content-text {
      background: #f5f5f5;
      padding: 12px;
      border-radius: 4px;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 300px;
      overflow-y: auto;
      line-height: 1.6;
      
      &.question-text {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
      }
      
      &.answer-text {
        background: #f5f5f5;
        border-left: 4px solid #4caf50;
      }
    }
  }
}
</style>
