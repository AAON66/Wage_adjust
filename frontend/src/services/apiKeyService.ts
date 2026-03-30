import api from './api';
import type { ApiKeyRead, ApiKeyCreatePayload, ApiKeyCreateResponse, ApiKeyRotateResponse } from '../types/api';

export async function createApiKey(payload: ApiKeyCreatePayload): Promise<ApiKeyCreateResponse> {
  const { data } = await api.post<ApiKeyCreateResponse>('/api-keys/', payload);
  return data;
}

export async function listApiKeys(): Promise<ApiKeyRead[]> {
  const { data } = await api.get<ApiKeyRead[]>('/api-keys/');
  return data;
}

export async function rotateApiKey(keyId: string): Promise<ApiKeyRotateResponse> {
  const { data } = await api.post<ApiKeyRotateResponse>(`/api-keys/${keyId}/rotate`);
  return data;
}

export async function revokeApiKey(keyId: string): Promise<ApiKeyRead> {
  const { data } = await api.post<ApiKeyRead>(`/api-keys/${keyId}/revoke`);
  return data;
}
