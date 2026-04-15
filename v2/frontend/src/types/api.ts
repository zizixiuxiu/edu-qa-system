/** API 类型定义 */

// 通用响应
export interface ApiResponse<T = any> {
  success: boolean;
  code?: string;
  message?: string;
  data?: T;
}

// 专家相关
export interface Expert {
  id: number;
  subject: string;
  name: string;
  model_type: string;
  status: 'active' | 'inactive' | 'training';
  knowledge_count: number;
  tier0_count: number;
  total_qa_count: number;
  accuracy_rate: number;
  created_at: string;
}

export interface ExpertStats {
  total_experts: number;
  active_experts: number;
  total_knowledge: number;
  total_qa: number;
}

// 聊天相关
export interface SendMessageRequest {
  session_id?: string;
  message: string;
  image_url?: string;
  force_expert?: string;
}

export interface SendMessageResponse {
  success: boolean;
  session_id: string;
  answer: string;
  expert_subject: string;
  expert_confidence: number;
  retrieved_knowledge_count: number;
  latency_ms: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  image_url?: string;
}

// 实验相关
export interface ExperimentConfig {
  name: string;
  description?: string;
  random_seed?: number;
  use_rag: boolean;
  use_expert_routing: boolean;
  enable_iteration: boolean;
  max_questions?: number;
  subject?: string | null;
  year?: string | null;
}

export interface ExperimentQueueItem {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed';
  config: ExperimentConfig;
  progress: number;
  current_question: number;
  total_questions: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ExperimentQueue {
  current_id: string | null;
  queue: ExperimentQueueItem[];
  total: number;
  pending: number;
  running: number;
  completed: number;
}

export interface BenchmarkProgress {
  status: 'idle' | 'running' | 'completed' | 'error';
  current: number;
  total: number;
  current_question: string;
  elapsed_time: number;
}
