import api from './api';
import type { CycleCreatePayload, CycleListResponse, CycleRecord, CycleUpdatePayload } from '../types/api';

export async function fetchCycles(): Promise<CycleListResponse> {
  const response = await api.get<CycleListResponse>('/cycles');
  return response.data;
}

export async function createCycle(payload: CycleCreatePayload): Promise<CycleRecord> {
  const response = await api.post<CycleRecord>('/cycles', payload);
  return response.data;
}

export async function updateCycle(cycleId: string, payload: CycleUpdatePayload): Promise<CycleRecord> {
  const response = await api.patch<CycleRecord>(`/cycles/${cycleId}`, payload);
  return response.data;
}

export async function publishCycle(cycleId: string): Promise<CycleRecord> {
  const response = await api.post<CycleRecord>(`/cycles/${cycleId}/publish`);
  return response.data;
}

export async function archiveCycle(cycleId: string): Promise<CycleRecord> {
  const response = await api.post<CycleRecord>(`/cycles/${cycleId}/archive`);
  return response.data;
}

export async function deleteCycle(cycleId: string): Promise<void> {
  await api.delete(`/cycles/${cycleId}`);
}
