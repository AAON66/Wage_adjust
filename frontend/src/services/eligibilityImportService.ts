import api from './api';

export type EligibilityImportType = 'performance_grades' | 'salary_adjustments' | 'hire_info' | 'non_statutory_leave';

export interface FeishuFieldInfo {
  field_id: string;
  field_name: string;
  type: number | null;
  ui_type: string | null;
}

export async function uploadEligibilityExcel(importType: EligibilityImportType, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/eligibility-import/excel?import_type=${importType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
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

export function getTemplateUrl(importType: EligibilityImportType): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8011/api/v1';
  return `${baseUrl}/eligibility-import/templates/${importType}?format=xlsx`;
}
