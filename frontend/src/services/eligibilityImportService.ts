import api from './api';
import type {
  ActiveJobResponse,
  ConfirmRequest,
  ConfirmResponse,
  EligibilityImportType,
  OverwriteMode,
  PreviewResponse,
} from '../types/api';

export type { EligibilityImportType };

export interface FeishuFieldInfo {
  field_id: string;
  field_name: string;
  type: number | null;
  ui_type: string | null;
}

/**
 * @deprecated Phase 32 起请改用 `uploadAndPreview` + `confirmImport` 两阶段提交。
 * 旧端点保留兼容性（OQ4 决议），新前端代码不应继续调用。
 */
export async function uploadEligibilityExcel(importType: EligibilityImportType, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/eligibility-import/excel?import_type=${importType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
}

export async function parseBitableUrl(url: string) {
  return api.post<{ app_token: string; table_id: string }>('/eligibility-import/feishu/parse-url', { url });
}

export async function fetchBitableFields(appToken: string, tableId: string) {
  return api.post<{ fields: FeishuFieldInfo[] }>('/eligibility-import/feishu/fields', {
    app_token: appToken,
    table_id: tableId,
  });
}

export async function triggerFeishuSync(
  syncType: EligibilityImportType,
  appToken: string,
  tableId: string,
  fieldMapping: Record<string, string>,
) {
  return api.post('/eligibility-import/feishu/sync', {
    sync_type: syncType,
    app_token: appToken,
    table_id: tableId,
    field_mapping: fieldMapping,
  });
}

export async function getSyncStatus(taskId: string) {
  const res = await api.get<{ status: string; result?: unknown; error?: string }>(`/tasks/${taskId}`);
  return res.data;
}

/**
 * @deprecated Phase 32 起请改用 `downloadTemplate(importType): Promise<void>`。
 * 旧实现返回 URL 字符串，被 `<a href target="_blank">` 消费会导致 Safari 内嵌渲染乱码（Pitfall 5）。
 * 保留以避免 Plan 06 改造前的过渡期 build 错误；未来 phase 可移除。
 */
export function getTemplateUrl(importType: EligibilityImportType): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8011/api/v1';
  return `${baseUrl}/eligibility-import/templates/${importType}?format=xlsx`;
}

// ===================== Phase 32 新增 =====================

/**
 * D-05 + IMPORT-02: blob 下载模板（替代旧 `getTemplateUrl`）。
 *
 * 用 `responseType: 'blob'` + `URL.createObjectURL` + 临时 `<a download>` 触发下载，
 * 复用 Phase 31 `feishuService.downloadUnmatchedCsv` 的 Safari 兼容模式。
 */
export async function downloadTemplate(importType: EligibilityImportType): Promise<void> {
  const response = await api.get<Blob>(
    `/eligibility-import/templates/${importType}?format=xlsx`,
    { responseType: 'blob' },
  );
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${importType}_template.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/**
 * D-06 + IMPORT-07: 上传 Excel + preview 阶段，不落库。
 * 返回 `PreviewResponse`（含 counters / rows × ≤200 / file_sha256）。
 *
 * 失败：
 * - 400: import_type 不支持 / 文件为空 / 行数超限
 * - 409: 同 import_type 已有活跃 job（body 顶层 `ImportConflictDetail`）
 * - 413: 文件 > 10MB
 * - 422: 文件类型不在白名单
 *
 * @param onUploadProgress 上传进度回调（0-100），由 axios `onUploadProgress` 派生
 */
export async function uploadAndPreview(
  importType: EligibilityImportType,
  file: File,
  onUploadProgress?: (percent: number) => void,
): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<PreviewResponse>(
    `/eligibility-import/excel/preview?import_type=${importType}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
      onUploadProgress: (e) => {
        if (onUploadProgress && e.total) {
          onUploadProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    },
  );
  return response.data;
}

/**
 * D-06 + IMPORT-05: 确认导入（落库）。
 * - merge 模式：直接传 `confirmReplace=false`（默认）
 * - replace 模式：必须 `confirmReplace=true`，否则后端 422 拦截（T-32-15）
 *
 * 失败：
 * - 404: job_id 不存在
 * - 409: 同 type 有其他 processing job / 当前 job 已 confirm/cancel
 * - 422: replace 模式 + confirmReplace=false
 */
export async function confirmImport(
  jobId: string,
  overwriteMode: OverwriteMode,
  confirmReplace: boolean = false,
): Promise<ConfirmResponse> {
  const body: ConfirmRequest = { overwrite_mode: overwriteMode, confirm_replace: confirmReplace };
  const response = await api.post<ConfirmResponse>(
    `/eligibility-import/excel/${jobId}/confirm`,
    body,
    { timeout: 120000 },
  );
  return response.data;
}

/**
 * D-06: 取消 previewing 状态 job + 删暂存文件。
 * 后端对终态 job 幂等返回 204（不抛异常）。
 */
export async function cancelImport(jobId: string): Promise<void> {
  await api.post(`/eligibility-import/excel/${jobId}/cancel`);
}

/**
 * D-18 + IMPORT-06: HR 进入 Tab 时查询是否存在活跃 job
 * （previewing / processing），用于禁用「选择文件」按钮 + 显示 banner。
 */
export async function getActiveImportJob(
  importType: EligibilityImportType,
): Promise<ActiveJobResponse> {
  const response = await api.get<ActiveJobResponse>(
    `/eligibility-import/excel/active?import_type=${importType}`,
  );
  return response.data;
}
