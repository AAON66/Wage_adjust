import api from './api';
import type { EvaluationRecord, TaskTriggerResponse } from '../types/api';

export async function generateEvaluation(submissionId: string): Promise<TaskTriggerResponse> {
  const response = await api.post<TaskTriggerResponse>('/evaluations/generate', { submission_id: submissionId });
  return response.data;
}

export async function regenerateEvaluation(submissionId: string): Promise<TaskTriggerResponse> {
  const response = await api.post<TaskTriggerResponse>('/evaluations/regenerate', { submission_id: submissionId });
  return response.data;
}

export async function fetchEvaluation(evaluationId: string): Promise<EvaluationRecord> {
  const response = await api.get<EvaluationRecord>(`/evaluations/${evaluationId}`);
  return response.data;
}

export async function fetchEvaluationBySubmission(submissionId: string): Promise<EvaluationRecord> {
  const response = await api.get<EvaluationRecord>(`/evaluations/by-submission/${submissionId}`);
  return response.data;
}

export async function submitManualReview(
  evaluationId: string,
  payload: { ai_level?: string; overall_score?: number; explanation: string; dimension_scores: Array<{ dimension_code: string; raw_score: number; rationale: string }> },
): Promise<EvaluationRecord> {
  const response = await api.patch<EvaluationRecord>(`/evaluations/${evaluationId}/manual-review`, payload);
  return response.data;
}

export async function submitHrReview(
  evaluationId: string,
  payload: { decision: 'approved' | 'returned'; comment?: string; final_score?: number },
): Promise<EvaluationRecord> {
  const response = await api.patch<EvaluationRecord>(`/evaluations/${evaluationId}/hr-review`, payload);
  return response.data;
}

export async function confirmEvaluation(evaluationId: string): Promise<void> {
  await api.post(`/evaluations/${evaluationId}/confirm`);
}
