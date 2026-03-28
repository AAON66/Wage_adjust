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

export async function downloadImportTemplate(importType: string, format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
  const response = await api.get(`/imports/templates/${importType}?format=${format}`, { responseType: 'blob' });
  return response.data;
}

export async function exportImportJob(jobId: string, format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
  const response = await api.get(`/imports/jobs/${jobId}/export?format=${format}`, { responseType: 'blob' });
  return response.data;
}

export async function deleteImportJob(jobId: string): Promise<{ deleted_job_id: string }> {
  const response = await api.delete<{ deleted_job_id: string }>(`/imports/jobs/${jobId}`);
  return response.data;
}

export async function bulkDeleteImportJobs(jobIds: string[]): Promise<{ deleted_job_ids: string[] }> {
  const response = await api.post<{ deleted_job_ids: string[] }>('/imports/jobs/bulk-delete', { job_ids: jobIds });
  return response.data;
}
