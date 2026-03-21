import api from './api';
import type { EmployeeHandbookListResponse, EmployeeHandbookRecord } from '../types/api';

export async function fetchHandbooks(): Promise<EmployeeHandbookListResponse> {
  const response = await api.get<EmployeeHandbookListResponse>('/handbooks');
  return response.data;
}

export async function uploadHandbook(file: File): Promise<EmployeeHandbookRecord> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<EmployeeHandbookRecord>('/handbooks', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function deleteHandbook(handbookId: string): Promise<{ deleted_handbook_id: string }> {
  const response = await api.delete<{ deleted_handbook_id: string }>(`/handbooks/${handbookId}`);
  return response.data;
}
