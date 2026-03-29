import api from './api';
import type {
  ApprovalCandidateListResponse,
  ApprovalListResponse,
  ApprovalStatusResponse,
  ApprovalStepPayload,
} from '../types/api';

export async function fetchApprovals(payload?: { includeAll?: boolean; decision?: string }): Promise<ApprovalListResponse> {
  const response = await api.get<ApprovalListResponse>('/approvals', {
    params: {
      include_all: payload?.includeAll ? true : undefined,
      decision: payload?.decision || undefined,
    },
  });
  return response.data;
}

export async function fetchApprovalCandidates(): Promise<ApprovalCandidateListResponse> {
  const response = await api.get<ApprovalCandidateListResponse>('/approvals/submission-candidates');
  return response.data;
}

export async function submitApproval(payload: { recommendationId: string; steps: ApprovalStepPayload[] }): Promise<ApprovalListResponse> {
  const response = await api.post<ApprovalListResponse>('/approvals/submit', {
    recommendation_id: payload.recommendationId,
    steps: payload.steps,
  });
  return response.data;
}

export async function submitDefaultApproval(recommendationId: string): Promise<ApprovalListResponse> {
  const response = await api.post<ApprovalListResponse>(`/approvals/submit-default/${recommendationId}`);
  return response.data;
}

export async function updateApprovalRoute(payload: { recommendationId: string; steps: ApprovalStepPayload[] }): Promise<ApprovalListResponse> {
  const response = await api.put<ApprovalListResponse>(`/approvals/recommendations/${payload.recommendationId}`, {
    steps: payload.steps,
  });
  return response.data;
}

export async function decideApproval(payload: { approvalId: string; decision: 'approved' | 'rejected'; comment?: string }): Promise<ApprovalStatusResponse> {
  const response = await api.patch<ApprovalStatusResponse>(`/approvals/${payload.approvalId}`, {
    decision: payload.decision,
    comment: payload.comment,
  });
  return response.data;
}

export async function deferApproval(payload: {
  approvalId: string;
  comment: string;
  deferUntil?: string;
  deferTargetScore?: number;
}): Promise<ApprovalStatusResponse> {
  const response = await api.patch<ApprovalStatusResponse>(`/approvals/${payload.approvalId}`, {
    decision: 'deferred',
    comment: payload.comment,
    defer_until: payload.deferUntil,
    defer_target_score: payload.deferTargetScore,
  });
  return response.data;
}

export async function fetchApprovalHistory(recommendationId: string): Promise<ApprovalListResponse> {
  const response = await api.get<ApprovalListResponse>(`/approvals/recommendations/${recommendationId}/history`);
  return response.data;
}
