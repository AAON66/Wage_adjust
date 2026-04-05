import { useState } from 'react';

import type { SharingRequestRecord } from '../../types/api';

interface SharingRequestCardProps {
  request: SharingRequestRecord;
  direction: 'incoming' | 'outgoing';
  onApprove: (id: string, finalPct: number) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onRevoke?: (id: string) => Promise<void>;
}

type StatusStyle = {
  bg: string;
  color: string;
  label: string;
};

const STATUS_STYLES: Record<SharingRequestRecord['status'], StatusStyle> = {
  pending: { bg: 'var(--color-warning-bg)', color: 'var(--color-warning)', label: '待审批' },
  approved: { bg: 'var(--color-success-bg)', color: 'var(--color-success)', label: '已审批' },
  rejected: { bg: 'var(--color-danger-bg)', color: 'var(--color-danger)', label: '已拒绝' },
  expired: { bg: 'var(--color-bg-subtle)', color: 'var(--color-steel)', label: '已超时' },
};

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  } catch {
    return iso;
  }
}

export function SharingRequestCard({ request, direction, onApprove, onReject, onRevoke }: SharingRequestCardProps) {
  const [showRatioEditor, setShowRatioEditor] = useState(false);
  const [editPct, setEditPct] = useState<number>(request.proposed_pct);
  const [isBusy, setIsBusy] = useState(false);

  const statusStyle = STATUS_STYLES[request.status];
  const isPending = request.status === 'pending';
  const isIncoming = direction === 'incoming';

  const statusPill = (
    <span
      style={{
        display: 'inline-block',
        padding: '3px 10px',
        fontSize: 12,
        fontWeight: 500,
        borderRadius: 4,
        background: statusStyle.bg,
        color: statusStyle.color,
      }}
    >
      {statusStyle.label}
    </span>
  );

  async function handleApproveClick() {
    const pct = Math.max(1, Math.min(99, Math.round(editPct)));
    setIsBusy(true);
    try {
      await onApprove(request.id, pct);
      setShowRatioEditor(false);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRejectClick() {
    // eslint-disable-next-line no-alert
    const ok = window.confirm('确认拒绝此共享申请？拒绝后对方将无法再次申请。');
    if (!ok) return;
    setIsBusy(true);
    try {
      await onReject(request.id);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRevokeClick() {
    if (!onRevoke) return;
    // eslint-disable-next-line no-alert
    const ok = window.confirm('确认撤销此审批？撤销后申请将恢复为待审批状态，贡献比例将被重置。');
    if (!ok) return;
    setIsBusy(true);
    try {
      await onRevoke(request.id);
    } finally {
      setIsBusy(false);
    }
  }

  const requesterOrOwner = isIncoming ? request.requester_name : request.original_uploader_name;
  const proposedRatio = `${request.proposed_pct}% : ${100 - request.proposed_pct}%`;
  const finalRatio =
    request.final_pct != null ? `${request.final_pct}% : ${100 - request.final_pct}%` : '-';
  // Display final_pct if approved, otherwise proposed_pct
  const displayRatio = request.final_pct != null ? finalRatio : proposedRatio;

  return (
    <>
      <tr>
        <td>{requesterOrOwner}</td>
        <td style={{ wordBreak: 'break-all' }}>{request.file_name}</td>
        <td>{formatDate(request.created_at)}</td>
        <td>{displayRatio}</td>
        <td>{statusPill}</td>
        {isIncoming ? (
          <td>
            {isPending ? (
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="action-primary"
                  disabled={isBusy}
                  onClick={() => setShowRatioEditor((v) => !v)}
                  style={{ height: 28, fontSize: 12.5, padding: '0 10px' }}
                  type="button"
                >
                  审批申请
                </button>
                <button
                  className="action-danger"
                  disabled={isBusy}
                  onClick={handleRejectClick}
                  style={{ height: 28, fontSize: 12.5, padding: '0 10px' }}
                  type="button"
                >
                  拒绝
                </button>
              </div>
            ) : request.status === 'approved' && onRevoke ? (
              <button
                className="action-secondary"
                disabled={isBusy}
                onClick={handleRevokeClick}
                style={{ height: 28, fontSize: 12.5, padding: '0 10px' }}
                type="button"
              >
                撤销审批
              </button>
            ) : (
              <span style={{ fontSize: 12.5, color: 'var(--color-steel)' }}>-</span>
            )}
          </td>
        ) : (
          <td>{request.status === 'approved' ? finalRatio : '-'}</td>
        )}
      </tr>
      {isIncoming && showRatioEditor && isPending ? (
        <tr>
          <td colSpan={6} style={{ padding: 0 }}>
            <div
              style={{
                background: 'var(--color-bg-subtle)',
                padding: 16,
                borderRadius: 8,
                margin: '8px 0',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <label style={{ fontSize: 12, color: 'var(--color-steel)' }}>调整贡献比例</label>
              <span style={{ fontSize: 13.5, color: 'var(--color-ink)' }}>
                申请者 {editPct}% : 您 {100 - editPct}%
              </span>
              <input
                className="toolbar-input"
                min={1}
                max={99}
                step={1}
                style={{ width: 80 }}
                type="number"
                value={editPct}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  if (Number.isFinite(v)) setEditPct(v);
                }}
              />
              <button
                className="action-primary"
                disabled={isBusy}
                onClick={handleApproveClick}
                style={{ height: 28, fontSize: 12.5, padding: '0 10px' }}
                type="button"
              >
                确认审批
              </button>
              <button
                onClick={() => setShowRatioEditor(false)}
                style={{
                  fontSize: 12.5,
                  color: 'var(--color-steel)',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
                type="button"
              >
                取消
              </button>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
