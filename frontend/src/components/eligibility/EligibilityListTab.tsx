import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '../../hooks/useAuth';
import {
  fetchEligibilityBatch,
  exportEligibilityExcel,
  createOverrideRequest,
  fetchDepartmentNames,
} from '../../services/eligibilityService';
import type { EligibilityBatchItem, EligibilityRuleResult } from '../../types/api';
import { EligibilityFilters, type EligibilityFilterValues } from './EligibilityFilters';

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  eligible: { label: '合格', color: '#16a34a', bg: '#dcfce7' },
  ineligible: { label: '不合格', color: '#dc2626', bg: '#fee2e2' },
  pending: { label: '待定', color: '#ca8a04', bg: '#fef9c3' },
};

const RULE_STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  eligible: { label: '合格', color: '#16a34a', bg: '#dcfce7' },
  ineligible: { label: '不合格', color: '#dc2626', bg: '#fee2e2' },
  data_missing: { label: '数据缺失', color: '#ca8a04', bg: '#fef9c3' },
  overridden: { label: '已覆盖', color: '#2563eb', bg: '#dbeafe' },
};

export function EligibilityListTab() {
  const { user } = useAuth();
  const role = user?.role ?? '';

  const [items, setItems] = useState<EligibilityBatchItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<EligibilityFilterValues>({});
  const [departments, setDepartments] = useState<string[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Override modal state
  const [overrideTarget, setOverrideTarget] = useState<EligibilityBatchItem | null>(null);
  const [overrideRules, setOverrideRules] = useState<string[]>([]);
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideSubmitting, setOverrideSubmitting] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchEligibilityBatch({ ...filters, page, page_size: pageSize });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      // error silently handled -- empty state shown
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    void fetchDepartmentNames().then(setDepartments).catch(() => {/* ignore */});
  }, []);

  function handleFilterChange(next: EligibilityFilterValues) {
    setFilters(next);
    setPage(1);
  }

  async function handleExport() {
    setExporting(true);
    try {
      await exportEligibilityExcel({ ...filters });
    } catch {
      // export error silently handled
    } finally {
      setExporting(false);
    }
  }

  function openOverrideModal(item: EligibilityBatchItem) {
    setOverrideTarget(item);
    setOverrideRules([]);
    setOverrideReason('');
    setOverrideError(null);
  }

  async function handleOverrideSubmit() {
    if (!overrideTarget || overrideRules.length === 0 || !overrideReason.trim()) return;
    setOverrideSubmitting(true);
    setOverrideError(null);
    try {
      await createOverrideRequest({
        employee_id: overrideTarget.employee_id,
        override_rules: overrideRules,
        reason: overrideReason.trim(),
      });
      setOverrideTarget(null);
      void loadData();
    } catch {
      setOverrideError('提交失败，请稍后重试。');
    } finally {
      setOverrideSubmitting(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canOverride = role === 'manager' || role === 'hrbp';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <EligibilityFilters
          onFilterChange={handleFilterChange}
          departments={departments}
          loading={loading && items.length === 0}
        />
        <button
          className="action-secondary flex items-center gap-2"
          disabled={exporting}
          onClick={() => void handleExport()}
          type="button"
        >
          {exporting ? '导出中...' : '导出 Excel'}
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded" style={{ background: 'var(--color-border)' }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="surface px-6 py-12 text-center text-sm text-steel">暂无数据</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-steel" style={{ borderColor: 'var(--color-border)' }}>
                  <th className="px-3 py-2">工号</th>
                  <th className="px-3 py-2">姓名</th>
                  <th className="px-3 py-2">部门</th>
                  <th className="px-3 py-2">岗位族</th>
                  <th className="px-3 py-2">职级</th>
                  <th className="px-3 py-2">资格状态</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const badge = STATUS_BADGE[item.overall_status];
                  const isExpanded = expandedId === item.employee_id;
                  return (
                    <tr key={item.employee_id} className="group">
                      <td colSpan={7} className="p-0">
                        <div
                          className="flex cursor-pointer items-center border-b px-0 py-0 transition-colors hover:bg-[var(--color-bg-surface-hover)]"
                          style={{ borderColor: 'var(--color-border)' }}
                          onClick={() => setExpandedId(isExpanded ? null : item.employee_id)}
                        >
                          <span className="w-auto min-w-0 flex-1 grid grid-cols-7 items-center">
                            <span className="px-3 py-2.5 text-ink">{item.employee_no}</span>
                            <span className="px-3 py-2.5 text-ink">{item.name}</span>
                            <span className="px-3 py-2.5 text-ink">{item.department}</span>
                            <span className="px-3 py-2.5 text-ink">{item.job_family ?? '--'}</span>
                            <span className="px-3 py-2.5 text-ink">{item.job_level ?? '--'}</span>
                            <span className="px-3 py-2.5">
                              {badge ? (
                                <span
                                  className="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                                  style={{ color: badge.color, background: badge.bg }}
                                >
                                  {badge.label}
                                </span>
                              ) : (
                                item.overall_status
                              )}
                            </span>
                            <span className="px-3 py-2.5 flex items-center gap-2">
                              <button
                                className="text-xs font-medium"
                                style={{ color: 'var(--color-primary)' }}
                                type="button"
                                onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : item.employee_id); }}
                              >
                                {isExpanded ? '收起' : '详情'}
                              </button>
                              {canOverride && item.overall_status === 'ineligible' && (
                                <button
                                  className="text-xs font-medium"
                                  style={{ color: '#ca8a04' }}
                                  type="button"
                                  onClick={(e) => { e.stopPropagation(); openOverrideModal(item); }}
                                >
                                  申请特殊审批
                                </button>
                              )}
                            </span>
                          </span>
                        </div>

                        {isExpanded && (
                          <div className="border-b px-6 py-3" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}>
                            <p className="mb-2 text-xs font-medium text-steel">规则详情</p>
                            <div className="grid gap-2 sm:grid-cols-2">
                              {item.rules.map((rule: EligibilityRuleResult) => {
                                const rb = RULE_STATUS_BADGE[rule.status];
                                return (
                                  <div key={rule.rule_code} className="flex items-start gap-2 rounded border px-3 py-2" style={{ borderColor: 'var(--color-border)' }}>
                                    <div className="min-w-0 flex-1">
                                      <p className="text-sm font-medium text-ink">{rule.rule_label}</p>
                                      <p className="mt-0.5 text-xs text-steel">{rule.detail}</p>
                                    </div>
                                    {rb && (
                                      <span
                                        className="inline-block shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
                                        style={{ color: rb.color, background: rb.bg }}
                                      >
                                        {rb.label}
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
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

      {/* Override Request Modal */}
      {overrideTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="surface mx-4 w-full max-w-md rounded-lg px-6 py-5">
            <h3 className="text-lg font-semibold text-ink">申请特殊审批</h3>
            <p className="mt-1 text-sm text-steel">
              为 {overrideTarget.name} ({overrideTarget.employee_no}) 申请覆盖不合格规则
            </p>

            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-steel">选择要覆盖的规则</p>
              {overrideTarget.rules
                .filter((r) => r.status === 'ineligible')
                .map((r) => (
                  <label key={r.rule_code} className="flex items-center gap-2 text-sm text-ink">
                    <input
                      checked={overrideRules.includes(r.rule_code)}
                      type="checkbox"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setOverrideRules((prev) => [...prev, r.rule_code]);
                        } else {
                          setOverrideRules((prev) => prev.filter((c) => c !== r.rule_code));
                        }
                      }}
                    />
                    {r.rule_label}
                  </label>
                ))}
            </div>

            <div className="mt-4">
              <p className="text-xs font-medium text-steel">申请原因</p>
              <textarea
                className="mt-1 w-full rounded border px-3 py-2 text-sm text-ink"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
                placeholder="请说明特殊审批的原因..."
                rows={3}
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
              />
            </div>

            {overrideError && (
              <p className="mt-2 text-sm" style={{ color: 'var(--color-danger)' }}>{overrideError}</p>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <button
                className="action-secondary"
                onClick={() => setOverrideTarget(null)}
                type="button"
              >
                取消
              </button>
              <button
                className="action-primary"
                disabled={overrideSubmitting || overrideRules.length === 0 || !overrideReason.trim()}
                onClick={() => void handleOverrideSubmit()}
                type="button"
              >
                {overrideSubmitting ? '提交中...' : '提交申请'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
