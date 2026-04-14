import api from './api';

export type EligibilityImportType =
  | 'performance_grades'
  | 'salary_adjustments'
  | 'hire_info'
  | 'non_statutory_leave';

export interface FeishuFieldInfo {
  field_id: string;
  field_name: string;
  type: number | null;
  ui_type: string | null;
}

interface TaskTriggerResponse {
  task_id: string;
  status: string;
}

interface BitableParseResponse {
  app_token: string;
  table_id: string;
}

interface FeishuFieldsResponse {
  fields: FeishuFieldInfo[];
}

export async function uploadEligibilityExcel(
  importType: EligibilityImportType,
  file: File,
): Promise<TaskTriggerResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<TaskTriggerResponse>(
    `/eligibility-import/excel?import_type=${importType}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
}

export async function parseBitableUrl(
  url: string,
): Promise<BitableParseResponse> {
  const response = await api.post<BitableParseResponse>(
    '/eligibility-import/feishu/parse-url',
    { url },
  );
  return response.data;
}

export async function fetchBitableFields(
  appToken: string,
  tableId: string,
): Promise<FeishuFieldsResponse> {
  const response = await api.post<FeishuFieldsResponse>(
    '/eligibility-import/feishu/fields',
    { app_token: appToken, table_id: tableId },
  );
  return response.data;
}

export async function triggerFeishuSync(
  syncType: EligibilityImportType,
  appToken: string,
  tableId: string,
  fieldMapping: Record<string, string>,
): Promise<TaskTriggerResponse> {
  const response = await api.post<TaskTriggerResponse>(
    '/eligibility-import/feishu/sync',
    {
      sync_type: syncType,
      app_token: appToken,
      table_id: tableId,
      field_mapping: fieldMapping,
    },
  );
  return response.data;
}

export function getTemplateUrl(importType: EligibilityImportType): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8011/api/v1';
  return `${baseUrl}/eligibility-import/templates/${importType}?format=xlsx`;
}
