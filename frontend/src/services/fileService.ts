import axios from 'axios';

import api from './api';
import type { ContributorInput, DuplicateFileError, EvidenceListResponse, FileDeleteResponse, ParseResultRecord, UploadedFileListResponse, UploadedFileRecord } from '../types/api';

const LONG_RUNNING_TIMEOUT = 120000;

export class DuplicateFileException extends Error {
  readonly detail: DuplicateFileError;

  constructor(detail: DuplicateFileError) {
    const msg = detail.message || '此文件已被提交过';
    super(msg);
    this.name = 'DuplicateFileException';
    this.detail = detail;
  }
}

export async function fetchSubmissionFiles(submissionId: string): Promise<UploadedFileListResponse> {
  const response = await api.get<UploadedFileListResponse>(`/submissions/${submissionId}/files`);
  return response.data;
}

export async function uploadSubmissionFiles(
  submissionId: string,
  files: File[],
  contributors?: ContributorInput[],
): Promise<UploadedFileListResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (contributors && contributors.length > 0) {
    formData.append('contributors', JSON.stringify(contributors));
  }
  try {
    const response = await api.post<UploadedFileListResponse>(`/submissions/${submissionId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      const data = error.response.data as DuplicateFileError;
      if (data.error === 'duplicate_file') {
        throw new DuplicateFileException(data);
      }
    }
    throw error;
  }
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
