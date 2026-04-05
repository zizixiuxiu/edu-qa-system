import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { experimentApi } from '../api'

export const useAppStore = defineStore('app', () => {
  // 状态
  const currentExperimentMode = ref('full_system')
  const isLoading = ref(false)
  const stats = ref({
    total_experts: 0,
    total_knowledge: 0,
    total_sessions: 0,
    total_sft_data: 0,
    today_sessions: 0,
    today_avg_response_time: 0,
    today_accuracy: 0
  })

  // 计算属性
  const experimentModeLabel = computed(() => {
    const labels: Record<string, string> = {
      'baseline': '基线组',
      'rag_only': 'RAG组',
      'expert_routing': '专家路由组',
      'full_system': '完整系统',
      'ablation_no_iteration': '消融-无迭代',
      'ablation_no_finetune': '消融-无微调'
    }
    return labels[currentExperimentMode.value] || currentExperimentMode.value
  })

  // 方法
  async function loadExperimentConfig() {
    try {
      const res: any = await experimentApi.getCurrentConfig()
      if (res.code === 200) {
        currentExperimentMode.value = res.data.mode
      }
    } catch (error) {
      console.error('加载实验配置失败:', error)
    }
  }

  async function switchExperimentMode(mode: string) {
    isLoading.value = true
    try {
      const res: any = await experimentApi.setConfig(mode)
      if (res.code === 200) {
        currentExperimentMode.value = mode
        return true
      }
    } catch (error) {
      console.error('切换实验模式失败:', error)
    } finally {
      isLoading.value = false
    }
    return false
  }

  async function loadDashboardStats() {
    try {
      const res: any = await experimentApi.getDashboard()
      if (res.code === 200) {
        stats.value = res.data
      }
    } catch (error) {
      console.error('加载统计数据失败:', error)
    }
  }

  return {
    currentExperimentMode,
    isLoading,
    stats,
    experimentModeLabel,
    loadExperimentConfig,
    switchExperimentMode,
    loadDashboardStats
  }
})
