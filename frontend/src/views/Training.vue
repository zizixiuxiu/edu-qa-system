<template>
  <div class="training-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <el-icon size="28"><Cpu /></el-icon>
        <h1>质检数据管理 Quality Data</h1>
      </div>
      <p class="header-desc">管理云端质检生成的错题知识点数据</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-value">{{ sftStats.total_unused }}</div>
        <div class="stat-label">待入库</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ sftStats.total_used }}</div>
        <div class="stat-label">已入库</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ sftDataList.length }}</div>
        <div class="stat-label">总计</div>
      </div>
    </div>

    <!-- 迭代结果（知识库数据） -->
    <div class="sft-section">
      <div class="section-header">
        <h3>📚 错题知识点（云端质检结果）</h3>
        <div class="filters">
          <el-button type="primary" size="small" @click="loadSFTData" :loading="sftLoading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <div v-if="selectedSftItems.length > 0" class="batch-actions">
        <el-button type="success" size="small" @click="batchAddToKnowledge" :loading="processing">
          <el-icon><Plus /></el-icon>
          批量入库 ({{ selectedSftItems.length }})
        </el-button>
        <el-button type="danger" size="small" @click="deleteSelectedItems" :loading="deleting">
          <el-icon><Delete /></el-icon>
          删除选中
        </el-button>
        <el-button size="small" @click="clearSelection">取消选择</el-button>
      </div>

      <el-table 
        ref="sftTableRef"
        :data="filteredSftDataList" 
        v-loading="sftLoading" 
        class="sft-table" 
        max-height="500"
        @selection-change="handleSelectionChange"
        @filter-change="handleSftFilterChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column type="index" label="序号" width="55" />
        <el-table-column prop="expert_name" label="专家" width="100"
          :filters="expertFilters"
          :filter-method="filterExpert"
          filter-placement="bottom"
        >
          <template #default="{ row }">
            <el-tag size="small" :color="getSubjectColor(row.expert_subject)" style="color: #fff; border: none;">
              {{ row.expert_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="问题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.question }}
          </template>
        </el-table-column>
        <el-table-column prop="quality_score" label="质量分" width="80">
          <template #default="{ row }">
            <el-tag :type="row.quality_score >= 4 ? 'success' : row.quality_score >= 3 ? 'warning' : 'danger'" size="small" effect="light">
              {{ row.quality_score.toFixed(2) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column 
          prop="status" 
          label="状态" 
          width="100"
          column-key="status"
          :filters="[
            { text: '待入库', value: 'pending' },
            { text: '已入库', value: 'trained' }
          ]"
          :filtered-value="sftStatusFilter"
        >
          <template #default="{ row }">
            <el-tag :type="row.status === 'trained' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.status === 'trained' ? '已入库' : '待入库' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="加入时间" width="140">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'pending'" 
              link 
              type="primary" 
              size="small"
              @click="addToKnowledge(row.id)"
              :loading="processingId === row.id"
            >
              加入知识库
            </el-button>
            <span v-else-if="row.status === 'duplicate'" class="text-gray">重复</span>
            <span v-else class="text-gray">已入库</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Cpu, Refresh, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { trainingApi } from '../api'

const sftLoading = ref(false)
const sftDataList = ref<Array<any>>([])
const sftStats = ref({ total_unused: 0, total_used: 0 })
const sftTableRef = ref<any>(null)
const selectedSftItems = ref<Array<any>>([])
const deleting = ref(false)
const processing = ref(false)
const processingId = ref<number | null>(null)

// 筛选状态
const sftStatusFilter = ref<string[]>([])
const sftExpertFilter = ref<string[]>([])

// 专家筛选选项（动态生成）
const expertFilters = computed(() => {
  const experts = new Map()
  sftDataList.value.forEach(item => {
    if (!experts.has(item.expert_id)) {
      experts.set(item.expert_id, { text: item.expert_name, value: item.expert_id })
    }
  })
  return Array.from(experts.values())
})

// 筛选方法
const filterExpert = (value: number, row: any) => {
  return row.expert_id === value
}

// 处理筛选变化
const handleSftFilterChange = (filters: any) => {
  if (filters.status) {
    sftStatusFilter.value = filters.status
  }
}

// 表格选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedSftItems.value = selection
}

// 清空选择
const clearSelection = () => {
  sftTableRef.value?.clearSelection()
  selectedSftItems.value = []
}

// 过滤显示的状态
const filteredSftDataList = computed(() => {
  let result = sftDataList.value
  
  // 状态筛选
  if (sftStatusFilter.value.length > 0) {
    result = result.filter((item: any) => sftStatusFilter.value.includes(item.status))
  }
  
  // 专家筛选
  if (sftExpertFilter.value.length > 0) {
    result = result.filter((item: any) => sftExpertFilter.value.includes(item.expert_id))
  }
  
  return result
})

// 加载SFT数据
const loadSFTData = async () => {
  sftLoading.value = true
  try {
    const res = await trainingApi.getPendingSessions() as any
    const data = res.data || res  // 兼容两种格式
    sftDataList.value = data.items || []
    
    // 更新统计
    sftStats.value = {
      total_unused: data.pending_count || 0,
      total_used: data.trained_count || 0
    }
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    sftLoading.value = false
  }
}

// 单条加入知识库
const addToKnowledge = async (id: number) => {
  processingId.value = id
  try {
    const res: any = await trainingApi.addToKnowledge([id])
    const data = res.data || res
    if (res.code === 200) {
      if (data.added_count > 0) {
        ElMessage.success(data.message || '已加入知识库')
        loadSFTData()  // 刷新列表
      } else if (data.duplicate_count > 0) {
        ElMessage.warning(data.message || '该内容已存在，未重复入库')
        // 标记重复的项（不刷新列表，保持状态可见）
        if (data.duplicate_ids && data.duplicate_ids.includes(id)) {
          const item = sftDataList.value.find((i: any) => i.id === id)
          if (item) {
            item.status = 'duplicate'
          }
        }
      } else {
        ElMessage.info(data.message || '未能入库')
        loadSFTData()
      }
    } else {
      ElMessage.error(res.message || data.message || '操作失败')
    }
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.response?.data?.message || '操作失败'
    ElMessage.error(msg)
  } finally {
    processingId.value = null
  }
}

// 批量加入知识库
const batchAddToKnowledge = async () => {
  if (selectedSftItems.value.length === 0) {
    ElMessage.warning('请先选择要入库的项')
    return
  }
  
  const pendingItems = selectedSftItems.value.filter(item => item.status === 'pending')
  if (pendingItems.length === 0) {
    ElMessage.warning('选中的项都已入库')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${pendingItems.length} 条记录加入知识库吗？`,
      '确认批量入库',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    processing.value = true
    const ids = pendingItems.map(item => item.id)
    
    const res: any = await trainingApi.addToKnowledge(ids)
    const data = res.data || res
    if (res.code === 200) {
      if (data.added_count > 0) {
        ElMessage.success(data.message || `成功将 ${data.added_count} 条记录加入知识库`)
      } else if (data.duplicate_count > 0) {
        ElMessage.warning(data.message || `共 ${data.duplicate_count} 条因内容重复未入库`)
      } else {
        ElMessage.info(data.message || '未能入库')
      }
      // 标记重复的项
      if (data.duplicate_ids && data.duplicate_ids.length > 0) {
        data.duplicate_ids.forEach((dupId: number) => {
          const item = sftDataList.value.find((i: any) => i.id === dupId)
          if (item) {
            item.status = 'duplicate'
          }
        })
      }
      clearSelection()
      loadSFTData()
    } else {
      ElMessage.error(res.message || data.message || '批量入库失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      const msg = error?.response?.data?.detail || error?.response?.data?.message || '批量入库失败'
      ElMessage.error(msg)
    }
  } finally {
    processing.value = false
  }
}

// 批量删除
const deleteSelectedItems = async () => {
  if (selectedSftItems.value.length === 0) {
    ElMessage.warning('请先选择要删除的项')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSftItems.value.length} 条记录吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    deleting.value = true
    const ids = selectedSftItems.value.map(item => item.id)
    
    await trainingApi.deletePendingSessions(ids)
    
    ElMessage.success('删除成功')
    clearSelection()
    loadSFTData()
  } catch (error: any) {
    if (error !== 'cancel') {
      const msg = error?.response?.data?.detail || '删除失败'
      ElMessage.error(msg)
    }
  } finally {
    deleting.value = false
  }
}

const getSubjectColor = (subject: string): string => {
  const map: Record<string, string> = {
    '数学': '#2E7D32',
    '语文': '#1565C0',
    '英语': '#E65100',
    '物理': '#00695C',
    '化学': '#C62828',
    '生物': '#558B2F',
    '政治': '#AD1457',
    '历史': '#4527A0',
    '地理': '#EF6C00'
  }
  return map[subject] || '#5C63A9'
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', { 
    month: 'short', day: 'numeric', 
    hour: '2-digit', minute: '2-digit' 
  })
}

onMounted(() => {
  loadSFTData()
})
</script>

<style scoped lang="scss">
.training-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  background: linear-gradient(135deg, #3F51B5 0%, #5C63A9 100%);
  border: 3px solid #111;
  box-shadow: 6px 6px 0 0 #111;
  padding: 24px;
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

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;

  .stat-card {
    background: white;
    border: 3px solid #111;
    box-shadow: 4px 4px 0 0 #111;
    padding: 16px;
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
      font-weight: 600;
      margin-top: 4px;
    }

    &.success { background: #E8F5E9; }
  }
}

.sft-section {
  flex: 1;
  background: white;
  border: 3px solid #111;
  box-shadow: 4px 4px 0 0 #111;
  display: flex;
  flex-direction: column;

  .section-header {
    padding: 16px 20px;
    border-bottom: 3px solid #111;
    display: flex;
    justify-content: space-between;
    align-items: center;

    h3 {
      font-family: 'Space Grotesk', sans-serif;
      margin: 0;
    }

    .filters {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }

  .sft-table {
    flex: 1;
    
    :deep(.el-table__header) {
      background: #f5f5f5;
    }
  }

  .batch-actions {
    padding: 12px 20px;
    background: #FFF3E0;
    border-bottom: 2px solid #FF9800;
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.text-gray {
  color: #999;
  font-size: 12px;
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
