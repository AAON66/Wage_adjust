import api from './api';
import type { CycleCreatePayload, CycleListResponse, CycleRecord } from '../types/api';

export async function fetchCycles(): Promise<CycleListResponse> {
  const response = await api.get<CycleListResponse>('/cycles');
  return response.data;
}

export async function createCycle(payload: CycleCreatePayload): Promise<CycleRecord> {
  const response = await api.post<CycleRecord>('/cycles', payload);
  return response.data;
}
