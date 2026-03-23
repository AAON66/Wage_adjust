import api from './api';
import type { SalaryRecommendationRecord, SalarySimulationResponse } from '../types/api';

const LONG_RUNNING_TIMEOUT = 120000;

export async function recommendSalary(evaluationId: string): Promise<SalaryRecommendationRecord> {
  const response = await api.post<SalaryRecommendationRecord>('/salary/recommend', { evaluation_id: evaluationId }, { timeout: LONG_RUNNING_TIMEOUT });
  return response.data;
}

export async function fetchSalaryRecommendationByEvaluation(evaluationId: string): Promise<SalaryRecommendationRecord> {
  const response = await api.get<SalaryRecommendationRecord>(`/salary/by-evaluation/${evaluationId}`);
  return response.data;
}

export async function fetchSalaryRecommendation(recommendationId: string): Promise<SalaryRecommendationRecord> {
  const response = await api.get<SalaryRecommendationRecord>(`/salary/${recommendationId}`);
  return response.data;
}

export async function updateSalaryRecommendation(
  recommendationId: string,
  payload: { final_adjustment_ratio: number; status?: string },
): Promise<SalaryRecommendationRecord> {
  const response = await api.patch<SalaryRecommendationRecord>(`/salary/${recommendationId}`, payload);
  return response.data;
}

export async function simulateSalary(payload: { cycle_id: string; budget_amount?: string; department?: string; job_family?: string }): Promise<SalarySimulationResponse> {
  const response = await api.post<SalarySimulationResponse>('/salary/simulate', payload);
  return response.data;
}
