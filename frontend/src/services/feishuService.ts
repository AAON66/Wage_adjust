import api from './api';
import type {
  FeishuConfigCreate,
  FeishuConfigRead,
  FeishuConfigUpdate,
  SyncLogRead,
  SyncTriggerResponse,
} from '../types/api';

export async function getFeishuConfig(): Promise<FeishuConfigRead> {
  const response = await api.get<FeishuConfigRead>('/feishu/config');
  return response.data;
}

export async function checkFeishuConfigExists(): Promise<boolean> {
  const response = await api.get<{ exists: boolean }>('/feishu/config-exists');
  return response.data.exists;
}

export async function createFeishuConfig(data: FeishuConfigCreate): Promise<FeishuConfigRead> {
  const response = await api.post<FeishuConfigRead>('/feishu/config', data);
  return response.data;
}

export async function updateFeishuConfig(configId: string, data: FeishuConfigUpdate): Promise<FeishuConfigRead> {
  const response = await api.put<FeishuConfigRead>(`/feishu/config/${configId}`, data);
  return response.data;
}

export async function triggerSync(mode: 'full' | 'incremental'): Promise<SyncTriggerResponse> {
  const response = await api.post<SyncTriggerResponse>('/feishu/sync', { mode });
  return response.data;
}

export async function getSyncLogs(limit?: number): Promise<SyncLogRead[]> {
  const params: Record<string, unknown> = {};
  if (limit !== undefined) {
    params.limit = limit;
  }
  const response = await api.get<SyncLogRead[]>('/feishu/sync-logs', { params });
  return response.data;
}

export async function getLatestSyncStatus(): Promise<SyncLogRead | null> {
  const response = await api.get<SyncLogRead | null>('/feishu/sync-status');
  return response.data;
}
