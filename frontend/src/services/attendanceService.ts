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
  const response = await api.get<{ data: AttendanceSummaryRead | null; message?: string }>(
    `/attendance/${employeeId}`,
    { params, signal },
  );
  return response.data.data ?? null;
}
