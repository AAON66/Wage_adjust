import api from './api';
import type { AuditLogListResponse } from '../types/api';

export interface AuditLogQueryParams {
  target_type?: string;
  target_id?: string;
  operator_id?: string;
  action?: string;
  from_dt?: string;
  to_dt?: string;
  limit?: number;
  offset?: number;
}

export async function getAuditLogs(params: AuditLogQueryParams): Promise<AuditLogListResponse> {
  const response = await api.get<AuditLogListResponse>('/audit/', { params });
  return response.data;
}
