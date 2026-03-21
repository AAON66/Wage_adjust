import api from './api';
import type { ApprovalListResponse, ApprovalStatusResponse, ApprovalStepPayload } from '../types/api';

export async function fetchApprovals(payload?: { includeAll?: boolean; decision?: string }): Promise<ApprovalListResponse> {
  const response = await api.get<ApprovalListResponse>('/approvals', {
    params: {
      include_all: payload?.includeAll ? true : undefined,
      decision: payload?.decision || undefined,
    },
  });
  return response.data;
}

export async function submitApproval(payload: { recommendationId: string; steps: ApprovalStepPayload[] }): Promise<ApprovalListResponse> {
  const response = await api.post<ApprovalListResponse>('/approvals/submit', {
    recommendation_id: payload.recommendationId,
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
