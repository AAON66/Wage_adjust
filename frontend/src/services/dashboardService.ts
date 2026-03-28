import api from './api';
import type {
  ApprovalPipelineResponse,
  DashboardDistributionResponse,
  DashboardSnapshotResponse,
  DepartmentDrilldownResponse,
  KpiSummaryResponse,
} from '../types/api';

export async function fetchDashboardSnapshot(cycleId?: string): Promise<DashboardSnapshotResponse> {
  const response = await api.get<DashboardSnapshotResponse>('/dashboard/snapshot', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}

export async function fetchKpiSummary(cycleId?: string): Promise<KpiSummaryResponse> {
  const response = await api.get<KpiSummaryResponse>('/dashboard/kpi-summary', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}

export async function fetchSalaryDistribution(cycleId?: string): Promise<DashboardDistributionResponse> {
  const response = await api.get<DashboardDistributionResponse>('/dashboard/salary-distribution', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}

export async function fetchApprovalPipeline(cycleId?: string): Promise<ApprovalPipelineResponse> {
  const response = await api.get<ApprovalPipelineResponse>('/dashboard/approval-pipeline', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}

export async function fetchDepartmentDrilldown(department: string, cycleId?: string): Promise<DepartmentDrilldownResponse> {
  const response = await api.get<DepartmentDrilldownResponse>('/dashboard/department-drilldown', {
    params: { department, ...(cycleId ? { cycle_id: cycleId } : {}) },
  });
  return response.data;
}

export async function fetchAiLevelDistribution(cycleId?: string): Promise<DashboardDistributionResponse> {
  const response = await api.get<DashboardDistributionResponse>('/dashboard/ai-level-distribution', {
    params: cycleId ? { cycle_id: cycleId } : undefined,
  });
  return response.data;
}
