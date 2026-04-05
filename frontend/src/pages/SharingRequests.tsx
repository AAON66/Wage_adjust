import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { SharingRequestCard } from '../components/sharing/SharingRequestCard';
import {
  approveSharingRequest,
  listSharingRequests,
  rejectSharingRequest,
  revokeSharingApproval,
} from '../services/sharingService';
import type { SharingRequestRecord } from '../types/api';

type Direction = 'incoming' | 'outgoing';

export function SharingRequestsPage() {
  const [direction, setDirection] = useState<Direction>('incoming');
  const [requests, setRequests] = useState<SharingRequestRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchRequests(dir: Direction) {
    setLoading(true);
    setError(null);
    try {
      const resp = await listSharingRequests(dir);
      setRequests(resp.items);
    } catch {
      setError('操作失败，请稍后重试。');
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchRequests(direction);
  }, [direction]);

  async function handleApprove(id: string, finalPct: number) {
    setError(null);
    try {
      await approveSharingRequest(id, finalPct);
      await fetchRequests(direction);
    } catch {
      setError('操作失败，请稍后重试。');
    }
  }

  async function handleReject(id: string) {
    setError(null);
    try {
      await rejectSharingRequest(id);
      await fetchRequests(direction);
    } catch {
      setError('操作失败，请稍后重试。');
    }
  }

  async function handleRevoke(id: string) {
    setError(null);
    try {
      await revokeSharingApproval(id);
      await fetchRequests(direction);
    } catch {
      setError('撤销失败，请稍后重试。');
    }
  }

  const isIncoming = direction === 'incoming';

  return (
    <AppShell
      title="共享申请"
      description="查看和管理文件共享申请。当他人上传与您相同内容的文件时，系统会自动发起共享申请。"
    >
      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
          <button
            className={'chip-button' + (isIncoming ? ' chip-button-active' : '')}
            onClick={() => setDirection('incoming')}
            type="button"
          >
            收到的申请
          </button>
          <button
            className={'chip-button' + (!isIncoming ? ' chip-button-active' : '')}
            onClick={() => setDirection('outgoing')}
            type="button"
          >
            发出的申请
          </button>
        </div>

        {loading ? (
          <p style={{ fontSize: 13, color: 'var(--color-steel)' }}>正在加载...</p>
        ) : requests.length === 0 ? (
          <div
            className="empty-state"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '48px 16px',
              textAlign: 'center',
            }}
          >
            <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)', margin: 0 }}>
              暂无共享申请
            </h3>
            <p
              style={{
                fontSize: 13,
                color: 'var(--color-steel)',
                maxWidth: 360,
                lineHeight: 1.6,
                marginTop: 8,
              }}
            >
              {isIncoming
                ? '当其他同事上传与您相同内容的文件时，相关申请会出现在此处。'
                : '当您上传与他人相同内容的文件时，发出的申请会出现在此处。'}
            </p>
          </div>
        ) : (
          <div className="table-shell">
            <table className="table-lite">
              <thead>
                <tr>
                  <th>{isIncoming ? '申请人' : '原上传者'}</th>
                  <th>文件名</th>
                  <th>申请日期</th>
                  <th>贡献比例</th>
                  <th>状态</th>
                  <th>{isIncoming ? '操作' : '最终比例'}</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => (
                  <SharingRequestCard
                    key={req.id}
                    request={req}
                    direction={direction}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    onRevoke={handleRevoke}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {error ? (
          <p style={{ fontSize: 12, color: 'var(--color-danger)', marginTop: 12 }}>{error}</p>
        ) : null}
      </section>
    </AppShell>
  );
}
