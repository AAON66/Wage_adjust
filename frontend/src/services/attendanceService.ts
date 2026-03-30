import api from './api';
import type { AttendanceListResponse, AttendanceSummaryRead } from '../types/api';

export async function listAttendance(params: {
  search?: string;
  department?: string;
  page?: number;
  page_size?: number;
}): Promise<AttendanceListResponse> {
  const response = await api.get<AttendanceListResponse>('/attendance/', { params });
  return response.data;
}

export async function getEmployeeAttendance(
  employeeId: string,
  period?: string,
  signal?: AbortSignal,
): Promise<AttendanceSummaryRead | null> {
  const params: Record<string, string> = {};
  if (period) {
    params.period = period;
  }
  const response = await api.get<AttendanceSummaryRead | { data: null; message: string }>(
    `/attendance/${employeeId}`,
    { params, signal },
  );
  if (response.data && 'data' in response.data && response.data.data === null) {
    return null;
  }
  return response.data as AttendanceSummaryRead;
}
