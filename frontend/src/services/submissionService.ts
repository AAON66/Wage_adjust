import api from './api';
import type { SubmissionListResponse, SubmissionRecord } from '../types/api';

export async function ensureSubmission(employeeId: string, cycleId: string): Promise<SubmissionRecord> {
  const response = await api.post<SubmissionRecord>('/submissions/ensure', {
    employee_id: employeeId,
    cycle_id: cycleId,
  });
  return response.data;
}

export async function fetchEmployeeSubmissions(employeeId: string): Promise<SubmissionListResponse> {
  const response = await api.get<SubmissionListResponse>(`/submissions/employee/${employeeId}`);
  return response.data;
}