import api from './api';
import type {
  FeishuConfigCreate,
  FeishuConfigRead,
  FeishuConfigUpdate,
  SyncLogRead,
  SyncLogSyncType,
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

export interface GetSyncLogsOptions {
  syncType?: SyncLogSyncType;
  page?: number;
  pageSize?: number;
}

/**
 * Phase 31: 升级签名为 options 对象，兼容 legacy `getSyncLogs(limit)` 调用。
 * - 传 number: legacy 用法，映射为 page=1 + page_size=limit
 * - 传 options: 可选 syncType / page / pageSize，映射为后端 sync_type / page / page_size
 */
export async function getSyncLogs(
  optsOrLimit?: GetSyncLogsOptions | number,
): Promise<SyncLogRead[]> {
  const params: Record<string, unknown> = {};
  if (typeof optsOrLimit === 'number') {
    params.page = 1;
    params.page_size = optsOrLimit;
  } else if (optsOrLimit) {
    if (optsOrLimit.syncType) params.sync_type = optsOrLimit.syncType;
    if (optsOrLimit.page) params.page = optsOrLimit.page;
    if (optsOrLimit.pageSize) params.page_size = optsOrLimit.pageSize;
  }
  const response = await api.get<SyncLogRead[]>('/feishu/sync-logs', { params });
  return response.data;
}

/**
 * Phase 31 / D-08: 下载指定 log_id 的未匹配工号 CSV。
 * 后端返回 Blob（text/csv; charset=utf-8），前端触发浏览器下载：
 * 文件名 `sync-log-{logId}-unmatched.csv`。
 */
export async function downloadUnmatchedCsv(logId: string): Promise<void> {
  const response = await api.get<Blob>(`/feishu/sync-logs/${logId}/unmatched.csv`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sync-log-${logId}-unmatched.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function getLatestSyncStatus(): Promise<SyncLogRead | null> {
  const response = await api.get<SyncLogRead | null>('/feishu/sync-status');
  return response.data;
}
