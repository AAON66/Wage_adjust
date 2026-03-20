import api from './api';
import type { EvaluationRecord } from '../types/api';

export async function generateEvaluation(submissionId: string): Promise<EvaluationRecord> {
  const response = await api.post<EvaluationRecord>('/evaluations/generate', { submission_id: submissionId });
  return response.data;
}

export async function regenerateEvaluation(submissionId: string): Promise<EvaluationRecord> {
  const response = await api.post<EvaluationRecord>('/evaluations/regenerate', { submission_id: submissionId });
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
  payload: { ai_level: string; explanation: string; dimension_scores: Array<{ dimension_code: string; raw_score: number; rationale: string }> },
): Promise<EvaluationRecord> {
  const response = await api.patch<EvaluationRecord>(`/evaluations/${evaluationId}/manual-review`, payload);
  return response.data;
}

export async function confirmEvaluation(evaluationId: string): Promise<void> {
  await api.post(`/evaluations/${evaluationId}/confirm`);
}
