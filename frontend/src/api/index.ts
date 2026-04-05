import axios from 'axios'

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 问答API
export const chatApi = {
  send: (data: { query: string; image?: string; session_id?: string }) => 
    api.post('/chat/send', data),
  uploadImage: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/chat/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

// 专家API
export const expertApi = {
  list: (subject?: string) => api.get('/experts/list', { params: { subject } }),
  get: (id: number) => api.get(`/experts/${id}`),
  create: (data: { subject: string; name?: string }) => api.post('/experts/create', data),
  listSubjects: () => api.get('/experts/subjects'),
  toggle: (id: number, is_active: boolean) => api.post(`/experts/${id}/toggle`, null, { params: { is_active } }),
  delete: (id: number) => api.delete(`/experts/${id}`),
  ensureDefaults: () => api.post('/experts/ensure-defaults'),
  // 专家知识库统计
  getKnowledgeStats: (id: number) => api.get(`/experts/${id}/knowledge-stats`),
  // 专家知识列表
  getKnowledgeList: (id: number, params?: { 
    knowledge_type?: string
    source_type?: string
    min_quality?: number
    page?: number
    page_size?: number
  }) => api.get(`/experts/${id}/knowledge`, { params })
}

// 实验API
export const experimentApi = {
  getPresets: () => api.get('/experiments/presets'),
  setConfig: (preset: string) => api.post('/experiments/config', { preset }),
  getCurrentConfig: () => api.get('/experiments/current-config'),
  getDashboard: () => api.get('/experiments/dashboard'),
  getComparison: () => api.get('/experiments/comparison'),
  getIterationProgress: (days?: number) => api.get('/experiments/iteration-progress', { params: { days } }),
  exportData: (format: string = 'json') => api.get('/experiments/export-data', { params: { format } })
}

// 基准测试API
export const benchmarkApi = {
  getStats: () => api.get('/benchmark/stats'),
  getDatasetInfo: () => api.get('/benchmark/datasets/info'),
  importDataset: (data: { source: string; path?: string; subject?: string }) => api.post('/benchmark/import', data),
  startTest: (data: { expert_id: number | null; mode: string; subject?: string; year?: string }) => 
    api.post('/benchmark/start', data),
  stopTest: () => api.post('/benchmark/stop'),
  resetTest: () => api.post('/benchmark/reset'),
  getProgress: () => api.get('/benchmark/progress'),
  getResults: (params: { page: number; page_size: number; filter: string }) => 
    api.get('/benchmark/results', { params }),
  getReport: () => api.get('/benchmark/report'),
  exportReport: (format: string = 'json') => api.get('/benchmark/report/export', { params: { format } }),
  // 报告管理
  listSavedReports: () => api.get('/benchmark/reports/list'),
  loadSavedReport: (filename: string) => api.get(`/benchmark/reports/load/${filename}`),
  deleteSavedReport: (filename: string) => api.delete(`/benchmark/reports/delete/${filename}`),
  compareReports: (filenames: string[]) => api.post('/benchmark/reports/compare', { filenames }),
  addToIteration: (data: { result_ids: number[] }) => api.post('/benchmark/add-to-iteration', data),
  deleteResults: (data: { result_ids: number[] }) => api.post('/benchmark/delete-results', data),
  // 迭代队列管理
  getIterationQueue: (expert_id?: number) => api.get('/benchmark/iteration-queue', { params: { expert_id } }),
  processIterationQueue: (expert_id: number) => api.post(`/benchmark/process-iteration-queue?expert_id=${expert_id}`),
  // SFT数据管理
  getSFTData: (params?: { expert_id?: number; is_used?: boolean; page?: number; page_size?: number }) => 
    api.get('/benchmark/sft-data', { params }),
  getSFTStats: () => api.get('/benchmark/sft-data/stats')
}

// 质检数据管理API
export const trainingApi = {
  // 待处理会话（质检完成但未入库）
  getPendingSessions: (expert_id?: number) => api.get('/training/pending-sessions', { params: { expert_id } }),
  // 批量删除待处理会话
  deletePendingSessions: (ids: number[]) => api.post('/training/pending-sessions/delete', { ids }),
  // 批量加入知识库
  addToKnowledge: (ids: number[]) => api.post('/training/add-to-knowledge', { ids })
}

// 知识库API
export const knowledgeApi = {
  list: (params?: { expert_id?: number; keyword?: string; page?: number; page_size?: number }) => 
    api.get('/knowledge/list', { params }),
  get: (id: number) => api.get(`/knowledge/${id}`),
  create: (data: { expert_id: number; content: string; source_type?: string }) => 
    api.post('/knowledge/create', data),
  update: (id: number, data: { expert_id: number; content: string; source_type?: string }) => 
    api.put(`/knowledge/${id}`, data),
  delete: (id: number) => api.delete(`/knowledge/${id}`),
  getStats: () => api.get('/knowledge/stats/overview')
}

export default api
