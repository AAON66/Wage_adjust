import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '../../hooks/useAuth';
import { fetchOverrides, decideOverride } from '../../services/eligibilityService';
import type { EligibilityOverrideRecord } from '../../types/api';

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '待HRBP审批', value: 'pending_hrbp' },
  { label: '待管理层审批', value: 'pending_admin' },
  { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
];

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pending_hrbp: { label: '待HRBP审批', color: '#ea580c', bg: '#fff7ed' },
  pending_admin: { label: '待管理层审批', color: '#2563eb', bg: '#dbeafe' },
  approved: { label: '已通过', color: '#16a34a', bg: '#dcfce7' },
  rejected: { label: '已拒绝', color: '#dc2626', bg: '#fee2e2' },
};

function formatDate(value: string | null | undefined): string {
  if (!value) return '--';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function OverrideRequestsTab() {
  const { user } = useAuth();
  const role = user?.role ?? '';

  const [items, setItems] = useState<EligibilityOverrideRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  // Decision modal state
  const [decisionTarget, setDecisionTarget] = useState<EligibilityOverrideRecord | null>(null);
  const [decisionType, setDecisionType] = useState<'approve' | 'reject'>('approve');
  const [decisionComment, setDecisionComment] = useState('');
  const [decisionSubmitting, setDecisionSubmitting] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchOverrides({ status: statusFilter || undefined, page, page_size: pageSize });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      // error silently handled
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page, pageSize]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  function openDecisionModal(item: EligibilityOverrideRecord, type: 'approve' | 'reject') {
    setDecisionTarget(item);
    setDecisionType(type);
    setDecisionComment('');
    setDecisionError(null);
  }

  async function handleDecisionSubmit() {
    if (!decisionTarget) return;
    setDecisionSubmitting(true);
    setDecisionError(null);
    try {
      await decideOverride(decisionTarget.id, {
        decision: decisionType,
        comment: decisionComment.trim() || undefined,
      });
      setDecisionTarget(null);
      void loadData();
    } catch {
      setDecisionError('操作失败，请稍后重试。');
    } finally {
      setDecisionSubmitting(false);
    }
  }

  function canAct(item: EligibilityOverrideRecord): boolean {
    if (item.status === 'pending_hrbp' && role === 'hrbp') return true;
    if (item.status === 'pending_admin' && role === 'admin') return true;
    return false;
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm text-steel">
          <span className="text-xs font-medium">状态筛选</span>
          <select
            className="rounded border px-3 py-1.5 text-sm text-ink"
            style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded" style={{ background: 'var(--color-border)' }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="surface px-6 py-12 text-center text-sm text-steel">暂无特殊申请记录</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-steel" style={{ borderColor: 'var(--color-border)' }}>
                  <th className="px-3 py-2">员工工号</th>
                  <th className="px-3 py-2">员工姓名</th>
                  <th className="px-3 py-2">申请人</th>
                  <th className="px-3 py-2">覆盖规则</th>
                  <th className="px-3 py-2">状态</th>
                  <th className="px-3 py-2">申请时间</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const badge = STATUS_BADGE[item.status];
                  const showActions = canAct(item);
                  return (
                    <tr key={item.id} className="border-b" style={{ borderColor: 'var(--color-border)' }}>
                      <td className="px-3 py-2.5 text-ink">{item.employee_no}</td>
                      <td className="px-3 py-2.5 text-ink">{item.employee_name}</td>
                      <td className="px-3 py-2.5 text-ink">{item.requester_name}</td>
                      <td className="px-3 py-2.5 text-ink">{item.override_rules.join(', ')}</td>
                      <td className="px-3 py-2.5">
                        {badge ? (
                          <span
                            className="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                            style={{ color: badge.color, background: badge.bg }}
                          >
                            {badge.label}
                          </span>
                        ) : (
                          item.status
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-steel">{formatDate(item.created_at)}</td>
                      <td className="px-3 py-2.5">
                        {showActions ? (
                          <div className="flex items-center gap-2">
                            <button
                              className="text-xs font-medium"
                              style={{ color: '#16a34a' }}
                              type="button"
                              onClick={() => openDecisionModal(item, 'approve')}
                            >
                              审批
                            </button>
                            <button
                              className="text-xs font-medium"
                              style={{ color: '#dc2626' }}
                              type="button"
                              onClick={() => openDecisionModal(item, 'reject')}
                            >
                              拒绝
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-steel">--</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between px-1 text-sm text-steel">
            <span>共 {total} 条</span>
            <div className="flex items-center gap-2">
              <button
                className="action-secondary px-3 py-1 text-xs"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                type="button"
              >
                上一页
              </button>
              <span className="text-xs">第 {page}/{totalPages} 页</span>
              <button
                className="action-secondary px-3 py-1 text-xs"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                type="button"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}

      {/* Decision Modal */}
      {decisionTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="surface mx-4 w-full max-w-md rounded-lg px-6 py-5">
            <h3 className="text-lg font-semibold text-ink">
              {decisionType === 'approve' ? '审批通过' : '拒绝申请'}
            </h3>
            <p className="mt-1 text-sm text-steel">
              {decisionTarget.employee_name} ({decisionTarget.employee_no}) 的特殊审批申请
            </p>

            <div className="mt-3 rounded border px-3 py-2 text-sm" style={{ borderColor: 'var(--color-border)' }}>
              <p className="text-xs font-medium text-steel">申请原因</p>
              <p className="mt-1 text-ink">{decisionTarget.reason}</p>
            </div>

            <div className="mt-4">
              <p className="text-xs font-medium text-steel">备注（可选）</p>
              <textarea
                className="mt-1 w-full rounded border px-3 py-2 text-sm text-ink"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
                placeholder="添加备注..."
                rows={2}
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
              />
            </div>

            {decisionError && (
              <p className="mt-2 text-sm" style={{ color: 'var(--color-danger)' }}>{decisionError}</p>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <button
                className="action-secondary"
                onClick={() => setDecisionTarget(null)}
                type="button"
              >
                取消
              </button>
              <button
                className={decisionType === 'approve' ? 'action-primary' : 'action-secondary'}
                disabled={decisionSubmitting}
                onClick={() => void handleDecisionSubmit()}
                style={decisionType === 'reject' ? { color: '#dc2626', borderColor: '#dc2626' } : undefined}
                type="button"
              >
                {decisionSubmitting ? '处理中...' : decisionType === 'approve' ? '确认通过' : '确认拒绝'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
