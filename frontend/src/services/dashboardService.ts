import api from './api';
import type { DashboardSnapshotResponse } from '../types/api';

export async function fetchDashboardSnapshot(cycleId?: string): Promise<DashboardSnapshotResponse> {
  const response = await api.get<DashboardSnapshotResponse>('/dashboard/snapshot', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}
