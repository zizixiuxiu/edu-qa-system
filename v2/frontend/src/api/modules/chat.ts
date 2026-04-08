/** 聊天 API */
import { http } from '../http';
import type { SendMessageRequest, SendMessageResponse, Message } from '../../types/api';

export const chatApi = {
  /** 发送消息 */
  sendMessage(data: SendMessageRequest): Promise<SendMessageResponse> {
    return http.post('/chat/send', data);
  },

  /** 提交反馈 */
  submitFeedback(data: {
    session_id: string;
    message_id: string;
    is_correct: boolean;
    score: number;
    suggestions?: string;
  }): Promise<{ success: boolean; message: string }> {
    return http.post('/chat/feedback', data);
  },

  /** 获取会话历史 */
  getSession(sessionId: string): Promise<{
    session_id: string;
    messages: Message[];
  }> {
    return http.get(`/chat/sessions/${sessionId}`);
  },
};
