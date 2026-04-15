/** 专家 API */
import { http } from '../http';
import type { Expert, ExpertStats } from '../../types/api';

export const expertApi = {
  /** 获取专家列表 */
  list(): Promise<Expert[]> {
    return http.get('/experts/list');
  },

  /** 获取专家详情 */
  get(id: number): Promise<Expert> {
    return http.get(`/experts/${id}`);
  },

  /** 更新专家 */
  update(id: number, data: Partial<Expert>): Promise<Expert> {
    return http.put(`/experts/${id}`, data);
  },

  /** 获取学科列表 */
  getSubjects(): Promise<{ subjects: string[] }> {
    return http.get('/experts/subjects/list');
  },

  /** 获取统计信息 */
  getStats(): Promise<ExpertStats> {
    return http.get('/experts/stats/summary');
  },
};
