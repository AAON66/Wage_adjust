import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ApprovalTable } from '../components/approval/ApprovalTable';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { decideApproval, fetchApprovals } from '../services/approvalService';
import type { ApprovalRecord } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载审批列表失败。';
  }
  return '加载审批列表失败。';
}

function formatIncrease(ratio: number): string {
  return `+${(ratio * 100).toFixed(1)}%`;
}

export function ApprovalsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<ApprovalRecord[]>([]);
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canViewAll = user?.role === 'admin' || user?.role === 'hrbp';
  const canSubmitApproval = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';

  async function loadApprovals(filter: 'all' | 'pending' | 'approved' | 'rejected' = decisionFilter) {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchApprovals({
        includeAll: canViewAll,
        decision: filter === 'all' ? undefined : filter,
      });
      setItems(response.items);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadApprovals(decisionFilter);
  }, [decisionFilter, canViewAll]);

  async function handleDecision(approvalId: string, decision: 'approved' | 'rejected') {
    setProcessingId(approvalId);
    setErrorMessage(null);
    try {
      await decideApproval({ approvalId, decision });
      await loadApprovals(decisionFilter);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setProcessingId(null);
    }
  }

  const summary = useMemo(() => {
    const allCount = items.length;
    const pendingCount = items.filter((item) => item.decision === 'pending').length;
    const approvedCount = items.filter((item) => item.decision === 'approved').length;
    const rejectedCount = items.filter((item) => item.decision === 'rejected').length;
    return { allCount, pendingCount, approvedCount, rejectedCount };
  }, [items]);

  const rows = useMemo(
    () => items.map((item) => ({
      id: item.id,
      employeeName: item.employee_name,
      department: item.department,
      cycleName: item.cycle_name,
      aiLevel: item.ai_level,
      recommendedIncrease: formatIncrease(item.final_adjustment_ratio),
      approver: item.approver_email,
      status: item.decision,
      canAct: item.decision === 'pending' && item.approver_id === user?.id,
    })),
    [items, user?.id],
  );

  return (
    <AppShell
      title="调薪审批中心"
      description="处理待审批与历史记录。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="rounded-full bg-[#2d5cff] px-5 py-2.5 text-sm font-medium text-white shadow-float" to="/salary-simulator">打开调薪模拟</Link>
        </>
      }
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['当前列表', String(summary.allCount), '当前筛选条件下的审批记录数。'],
          ['待处理', String(summary.pendingCount), '仍待当前流程节点处理的审批。'],
          ['已通过', String(summary.approvedCount), '已明确通过的审批记录。'],
          ['已驳回', String(summary.rejectedCount), '已结束或退回的审批记录。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface animate-fade-up px-6 py-5 lg:px-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {[
              ['pending', '待处理'],
              ['approved', '已通过'],
              ['rejected', '已驳回'],
              ['all', '全部'],
            ].map(([value, label]) => (
              <button
                className={`chip-button ${decisionFilter === value ? 'chip-button-active' : ''}`}
                key={value}
                onClick={() => setDecisionFilter(value as typeof decisionFilter)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-sm text-steel">{canViewAll ? '当前为全局审批视图。' : '当前展示分配给本账号的审批任务。'}</p>
        </div>
      </section>

      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载审批列表...</p> : null}

      {!isLoading && rows.length === 0 ? (
        <section className="surface px-6 py-8 text-center">
          <h2 className="text-xl font-semibold text-ink">当前没有可展示的审批记录</h2>
          <p className="mt-2 text-sm leading-6 text-steel">先生成调薪建议，再来这里审批。</p>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <Link className="rounded-full bg-[#2d5cff] px-5 py-3 text-sm font-medium text-white shadow-float" to="/employees">前往员工评估</Link>
            <Link className="chip-button" to="/salary-simulator">查看调薪模拟</Link>
          </div>
          {!canSubmitApproval ? <p className="mt-4 text-sm text-amber-700">当前账号角色无法提交审批。请使用主管、HRBP 或管理员账号发起审批。</p> : null}
        </section>
      ) : (
        <ApprovalTable
          onApprove={(approvalId) => void handleDecision(approvalId, 'approved')}
          onReject={(approvalId) => void handleDecision(approvalId, 'rejected')}
          processingId={processingId}
          rows={rows}
        />
      )}
    </AppShell>
  );
}
