import api from './api';
import type { ImportJobListResponse, ImportJobRecord } from '../types/api';

export async function fetchImportJobs(): Promise<ImportJobListResponse> {
  const response = await api.get<ImportJobListResponse>('/imports/jobs');
  return response.data;
}

export async function createImportJob(importType: string, file: File): Promise<ImportJobRecord> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<ImportJobRecord>(`/imports/jobs?import_type=${encodeURIComponent(importType)}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function downloadImportTemplate(importType: string): Promise<Blob> {
  const response = await api.get(`/imports/templates/${importType}`, { responseType: 'blob' });
  return response.data;
}

export async function exportImportJob(jobId: string): Promise<Blob> {
  const response = await api.get(`/imports/jobs/${jobId}/export`, { responseType: 'blob' });
  return response.data;
}
