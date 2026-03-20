import api from './api';
import type { EvidenceListResponse, UploadedFileListResponse } from '../types/api';

export async function fetchSubmissionFiles(submissionId: string): Promise<UploadedFileListResponse> {
  const response = await api.get<UploadedFileListResponse>(`/submissions/${submissionId}/files`);
  return response.data;
}

export async function uploadSubmissionFiles(submissionId: string, files: File[]): Promise<UploadedFileListResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const response = await api.post<UploadedFileListResponse>(`/submissions/${submissionId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function parseFile(fileId: string): Promise<void> {
  await api.post(`/files/${fileId}/parse`);
}

export async function parseAllSubmissionFiles(submissionId: string): Promise<UploadedFileListResponse> {
  const response = await api.post<UploadedFileListResponse>(`/submissions/${submissionId}/parse-all`);
  return response.data;
}

export async function fetchSubmissionEvidence(submissionId: string): Promise<EvidenceListResponse> {
  const response = await api.get<EvidenceListResponse>(`/submissions/${submissionId}/evidence`);
  return response.data;
}