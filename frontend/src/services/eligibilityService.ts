import api from './api';
import type {
  EligibilityBatchResponse,
  EligibilityOverrideRecord,
  EligibilityOverrideListResponse,
  EligibilityOverrideCreatePayload,
  EligibilityOverrideDecisionPayload,
  DepartmentListResponse,
  EligibilityResult,
  EligibilityResultWithTimestamp,
} from '../types/api';

export interface EligibilityBatchParams {
  department?: string;
  status?: string;
  rule?: string;
  job_family?: string;
  job_level?: string;
  page?: number;
  page_size?: number;
  year?: number;
}

export async function fetchEligibilityBatch(params: EligibilityBatchParams): Promise<EligibilityBatchResponse> {
  const response = await api.get<EligibilityBatchResponse>('/eligibility/batch', { params });
  return response.data;
}

export async function exportEligibilityExcel(params: EligibilityBatchParams): Promise<void> {
  const response = await api.get('/eligibility/batch/export', {
    params,
    responseType: 'blob',
  });

  const contentDisposition = response.headers['content-disposition'] as string | undefined;
  let filename = 'eligibility_export.xlsx';
  if (contentDisposition) {
    const match = /filename[^;=\n]*=(['""]?)([^'"";\n]*)\1/.exec(contentDisposition);
    if (match?.[2]) {
      filename = match[2];
    }
  }

  const blob = new Blob([response.data as BlobPart], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function createOverrideRequest(payload: EligibilityOverrideCreatePayload): Promise<EligibilityOverrideRecord> {
  const response = await api.post<EligibilityOverrideRecord>('/eligibility/overrides', payload);
  return response.data;
}

export async function fetchOverrides(params: { status?: string; page?: number; page_size?: number }): Promise<EligibilityOverrideListResponse> {
  const response = await api.get<EligibilityOverrideListResponse>('/eligibility/overrides', { params });
  return response.data;
}

export async function fetchOverrideDetail(id: string): Promise<EligibilityOverrideRecord> {
  const response = await api.get<EligibilityOverrideRecord>(`/eligibility/overrides/${id}`);
  return response.data;
}

export async function decideOverride(id: string, payload: EligibilityOverrideDecisionPayload): Promise<EligibilityOverrideRecord> {
  const response = await api.post<EligibilityOverrideRecord>(`/eligibility/overrides/${id}/decide`, payload);
  return response.data;
}

export async function fetchEmployeeEligibility(
  employeeId: string,
): Promise<EligibilityResult> {
  const response = await api.get<EligibilityResult>(
    `/eligibility/${employeeId}`,
  );
  return response.data;
}

/**
 * Phase 32.1 D-18: 员工自助查询本人调薪资格（无参数路由）
 * 后端端点：GET /api/v1/eligibility/me
 * 错误码：401 未鉴权 / 422 未绑定员工 / 404 档案缺失 / 500 内部错误
 */
export async function fetchMyEligibility(): Promise<EligibilityResultWithTimestamp> {
  const response = await api.get<EligibilityResultWithTimestamp>('/eligibility/me');
  return response.data;
}

export async function fetchDepartmentNames(): Promise<string[]> {
  const response = await api.get<DepartmentListResponse>('/departments');
  return response.data.items.map((d) => d.name);
}
