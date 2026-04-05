<template>
  <div class="dashboard">
    <h1 class="page-title">📊 系统概览 Dashboard</h1>
    
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card pink">
        <div class="stat-icon">🎓</div>
        <div class="stat-value">{{ stats.total_experts }}</div>
        <div class="stat-label">专家数量 Experts</div>
      </div>
      
      <div class="stat-card yellow">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{{ stats.total_knowledge }}</div>
        <div class="stat-label">知识条目 Knowledge</div>
      </div>
      
      <div class="stat-card teal">
        <div class="stat-icon">💬</div>
        <div class="stat-value">{{ stats.total_sessions }}</div>
        <div class="stat-label">问答总数 Sessions</div>
      </div>
      
      <div class="stat-card peach">
        <div class="stat-icon">🤖</div>
        <div class="stat-value">{{ stats.total_sft_data }}</div>
        <div class="stat-label">微调数据 SFT Data</div>
      </div>
    </div>

    <!-- 今日数据 -->
    <div class="today-section">
      <h2 class="section-title">📈 今日数据 Today</h2>
      <div class="today-grid">
        <div class="today-item">
          <span class="today-number">{{ stats.today_sessions }}</span>
          <span class="today-label">今日问答</span>
        </div>
        <div class="today-item">
          <span class="today-number">{{ stats.today_avg_response_time }}ms</span>
          <span class="today-label">平均响应</span>
        </div>
        <div class="today-item">
          <span class="today-number">{{ stats.today_accuracy }}%</span>
          <span class="today-label">准确率</span>
        </div>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="status-section">
      <h2 class="section-title">⚙️ 系统状态 System Status</h2>
      <div class="status-list">
        <div class="status-item">
          <span class="status-label">专家路由 Expert Routing</span>
          <el-tag 
            :type="config.expert_routing ? 'success' : 'info'"
            effect="light"
            :class="config.expert_routing ? 'status-tag-enabled' : 'status-tag-disabled'"
          >
            {{ config.expert_routing ? '已启用' : '已禁用' }}
          </el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">知识检索 RAG</span>
          <el-tag 
            :type="config.rag ? 'success' : 'info'"
            effect="light"
            :class="config.rag ? 'status-tag-enabled' : 'status-tag-disabled'"
          >
            {{ config.rag ? '已启用' : '已禁用' }}
          </el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">自我迭代 Self-Iteration</span>
          <el-tag 
            :type="config.self_iteration ? 'success' : 'info'"
            effect="light"
            :class="config.self_iteration ? 'status-tag-enabled' : 'status-tag-disabled'"
          >
            {{ config.self_iteration ? '已启用' : '已禁用' }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <h2 class="section-title">🚀 快速操作 Quick Actions</h2>
      <div class="action-buttons">
        <router-link to="/chat">
          <el-button type="primary" size="large">
            <el-icon><ChatDotRound /></el-icon>
            开始问答
          </el-button>
        </router-link>
        <router-link to="/experiments">
          <el-button type="warning" size="large">
            <el-icon><Setting /></el-icon>
            实验配置
          </el-button>
        </router-link>
        <router-link to="/analytics">
          <el-button type="success" size="large">
            <el-icon><TrendCharts /></el-icon>
            查看数据
          </el-button>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { experimentApi } from '../api'

const appStore = useAppStore()
const stats = ref(appStore.stats)
const config = ref({
  expert_routing: true,
  rag: true,
  self_iteration: true
})

onMounted(async () => {
  await appStore.loadDashboardStats()
  stats.value = appStore.stats
  
  // 加载当前配置
  const res: any = await experimentApi.getCurrentConfig()
  if (res.code === 200) {
    config.value = res.data
  }
})
</script>

<style scoped lang="scss">
.dashboard {
  max-width: 1200px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 32px 0;
  text-transform: uppercase;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 24px;
  text-align: center;
  transition: all 0.2s ease;
}
.stat-card:hover {
  transform: translate(-4px, -4px);
  box-shadow: var(--shadow-hover);
}
.stat-card.pink { background: var(--memphis-pink); }
.stat-card.yellow { background: var(--memphis-yellow); }
.stat-card.teal { background: var(--memphis-teal); }
.stat-card.peach { background: var(--memphis-peach); }

.stat-icon {
  font-size: 40px;
  margin-bottom: 8px;
}
.stat-value {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 4px;
}
.stat-label {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--memphis-black);
  opacity: 0.95;
  text-shadow: 1px 1px 0 rgba(0,0,0,0.1);
}

.today-section, .status-section, .quick-actions {
  background: var(--memphis-white);
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  text-transform: uppercase;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 3px solid var(--memphis-black);
  color: var(--memphis-black);
}

.today-grid {
  display: flex;
  gap: 48px;
}
.today-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.today-number {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  color: var(--memphis-blue);
  text-shadow: 2px 2px 0 rgba(92, 99, 169, 0.2);
}
.today-label {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--memphis-black);
  opacity: 0.9;
}

.status-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border: 2px solid #ddd;
}
.status-label {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--memphis-black);
}

/* 系统状态标签样式 */
:deep(.status-tag-enabled) {
  background-color: var(--memphis-teal) !important;
  border-color: var(--memphis-black) !important;
  color: var(--memphis-black) !important;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
}
:deep(.status-tag-disabled) {
  background-color: #e0e0e0 !important;
  border-color: var(--memphis-black) !important;
  color: #666 !important;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
}

.action-buttons {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.action-buttons .el-button {
  font-size: 16px;
  padding: 16px 32px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .today-grid {
    flex-direction: column;
    gap: 16px;
  }
  .status-list {
    grid-template-columns: 1fr;
  }
}
</style>
