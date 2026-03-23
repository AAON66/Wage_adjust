import api from './api';
import type { EvidenceListResponse, FileDeleteResponse, ParseResultRecord, UploadedFileListResponse, UploadedFileRecord } from '../types/api';

const LONG_RUNNING_TIMEOUT = 120000;

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

export async function importGitHubSubmissionFile(submissionId: string, url: string): Promise<UploadedFileRecord> {
  const response = await api.post<UploadedFileRecord>(`/submissions/${submissionId}/github-import`, { url }, { timeout: LONG_RUNNING_TIMEOUT });
  return response.data;
}

export async function replaceSubmissionFile(fileId: string, file: File): Promise<UploadedFileRecord> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.put<UploadedFileRecord>(`/files/${fileId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function deleteSubmissionFile(fileId: string): Promise<FileDeleteResponse> {
  const response = await api.delete<FileDeleteResponse>(`/files/${fileId}`);
  return response.data;
}

export async function parseFile(fileId: string): Promise<ParseResultRecord> {
  const response = await api.post<ParseResultRecord>(`/files/${fileId}/parse`, undefined, { timeout: LONG_RUNNING_TIMEOUT });
  return response.data;
}

export async function parseAllSubmissionFiles(submissionId: string): Promise<UploadedFileListResponse> {
  const response = await api.post<UploadedFileListResponse>(`/submissions/${submissionId}/parse-all`, undefined, { timeout: LONG_RUNNING_TIMEOUT });
  return response.data;
}

export async function fetchSubmissionEvidence(submissionId: string): Promise<EvidenceListResponse> {
  const response = await api.get<EvidenceListResponse>(`/submissions/${submissionId}/evidence`);
  return response.data;
}
