import api from './api';
import type {
  CheckDuplicateResponse,
  SharingRequestRecord,
  SharingRequestListResponse,
} from '../types/api';

export async function checkDuplicate(
  contentHash: string,
  submissionId: string,
): Promise<CheckDuplicateResponse> {
  const res = await api.post<CheckDuplicateResponse>('/files/check-duplicate', {
    content_hash: contentHash,
    submission_id: submissionId,
  });
  return res.data;
}

export async function listSharingRequests(
  direction: 'incoming' | 'outgoing' = 'incoming',
): Promise<SharingRequestListResponse> {
  const res = await api.get<SharingRequestListResponse>('/sharing-requests', {
    params: { direction },
  });
  return res.data;
}

// NOTE: No createSharingRequest function. Sharing requests are created atomically
// by the upload endpoint with allow_duplicate=true (REVIEW FIX #2).

export async function approveSharingRequest(
  requestId: string,
  finalPct: number,
): Promise<SharingRequestRecord> {
  const res = await api.post<SharingRequestRecord>(
    `/sharing-requests/${requestId}/approve`,
    { final_pct: finalPct },
  );
  return res.data;
}

export async function rejectSharingRequest(
  requestId: string,
): Promise<SharingRequestRecord> {
  const res = await api.post<SharingRequestRecord>(
    `/sharing-requests/${requestId}/reject`,
  );
  return res.data;
}

export async function revokeSharingApproval(
  requestId: string,
): Promise<SharingRequestRecord> {
  const res = await api.post<SharingRequestRecord>(
    `/sharing-requests/${requestId}/revoke`,
  );
  return res.data;
}

export async function getPendingSharingCount(): Promise<number> {
  const res = await api.get<{ count: number }>('/sharing-requests/pending-count');
  return res.data.count;
}
