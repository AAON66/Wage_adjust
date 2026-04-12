import api from './api';
import type { TaskStatusResponse } from '../types/api';

export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await api.get<TaskStatusResponse>(`/tasks/${taskId}`);
  return response.data;
}
