/** 实验 API */
import { http } from '../http';
import type {
  ExperimentConfig,
  ExperimentQueue,
  ExperimentQueueItem,
  BenchmarkProgress,
} from '../../types/api';

export const experimentApi = {
  /** 创建实验 */
  create(experiments: ExperimentConfig[]): Promise<{
    success: boolean;
    experiment_ids: string[];
    message: string;
  }> {
    return http.post('/experiments/create', { experiments });
  },

  /** 获取队列 */
  getQueue(): Promise<ExperimentQueue> {
    return http.get('/experiments/queue');
  },

  /** 启动实验 */
  start(): Promise<{
    success: boolean;
    experiment?: ExperimentQueueItem;
    message?: string;
  }> {
    return http.post('/experiments/start');
  },

  /** 清空队列 */
  clear(): Promise<{ success: boolean; message: string }> {
    return http.post('/experiments/clear');
  },

  /** 获取进度 */
  getProgress(): Promise<BenchmarkProgress> {
    return http.get('/experiments/progress');
  },

  /** 一键运行全部实验 */
  runAll(): Promise<{
    success: boolean;
    message: string;
    experiment_count: number;
    started: boolean;
  }> {
    return http.post('/experiments/run-all');
  },
};
