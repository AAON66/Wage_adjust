import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApprovalTable } from '../components/approval/ApprovalTable';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { decideApproval, deferApproval, fetchApprovalCandidates, fetchApprovals, submitDefaultApproval, updateApprovalRoute } from '../services/approvalService';
import { fetchUsers } from '../services/userAdminService';
import type { ApprovalCandidateRecord, ApprovalRecord, ApprovalStepPayload, UserProfile } from '../types/api';

type DetailSelection =
  | { kind: 'candidate'; id: string }
  | { kind: 'approval'; id: string }
  | null;

type ActionMode = 'approved' | 'rejected' | 'deferred';
type DeferMode = 'time' | 'score';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载调薪审批中心失败。'
    );
  }
  return '加载调薪审批中心失败。';
}

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '--';
  }
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value));
}

function formatRecommendationStatus(status: string): string {
  return (
    {
      draft: '未生成',
      recommended: '待发起审批',
      adjusted: '人工调整后待发起',
      pending_approval: '审批中',
      approved: '已审批',
      rejected: '已驳回',
      deferred: '已暂缓',
      locked: '已锁定',
    }[status] ?? status
  );
}

function formatStepName(value: string): string {
  return (
    {
      hrbp_review: 'HRBP 复核',
      admin_final_review: '管理员终审',
      hr_review: 'HR 审核',
      committee: '审批会签',
    }[value] ?? value
  );
}

function buildDeferSummary(item: { defer_until?: string | null; defer_target_score?: number | null; defer_reason?: string | null }): string {
  const parts: string[] = [];
  if (item.defer_until) {
    parts.push(`暂缓至 ${formatDate(item.defer_until)}`);
  }
  if (item.defer_target_score != null) {
    parts.push(`达标分数 ${item.defer_target_score}`);
  }
  if (item.defer_reason) {
    parts.push(`原因：${item.defer_reason}`);
  }
  return parts.join('；');
}

function buildStepName(role: string, index: number, total: number): string {
  if (index === 0 && role === 'hrbp') {
    return 'hrbp_review';
  }
  if (index === total - 1 && role === 'admin') {
    return 'admin_final_review';
  }
  return `custom_review_${index + 1}`;
}

function extractRouteEmails(routePreview: string[]): string[] {
  return routePreview
    .map((item) => item.split('->')[1]?.trim().toLowerCase())
    .filter((item): item is string => Boolean(item));
}

export function ApprovalsPage() {
  const { user } = useAuth();
  const [includeAll, setIncludeAll] = useState(user?.role === 'admin');
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'pending' | 'approved' | 'rejected' | 'deferred'>('pending');
  const [records, setRecords] = useState<ApprovalRecord[]>([]);
  const [candidates, setCandidates] = useState<ApprovalCandidateRecord[]>([]);
  const [approvers, setApprovers] = useState<UserProfile[]>([]);
  const [selection, setSelection] = useState<DetailSelection>(null);
  const [routeDraftApproverIds, setRouteDraftApproverIds] = useState<string[]>([]);
  const [actionMode, setActionMode] = useState<ActionMode>('approved');
  const [decisionComment, setDecisionComment] = useState('');
  const [deferMode, setDeferMode] = useState<DeferMode>('time');
  const [deferDate, setDeferDate] = useState('');
  const [deferScore, setDeferScore] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmittingCandidateId, setIsSubmittingCandidateId] = useState<string | null>(null);
  const [processingApprovalId, setProcessingApprovalId] = useState<string | null>(null);
  const [editingRecommendationId, setEditingRecommendationId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canSubmitApproval = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';

  async function loadData() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [approvalResponse, candidateResponse, userResponse] = await Promise.all([
        fetchApprovals({
          includeAll,
          decision: decisionFilter === 'all' ? undefined : decisionFilter,
        }),
        canSubmitApproval ? fetchApprovalCandidates() : Promise.resolve({ items: [], total: 0 }),
        canSubmitApproval ? fetchUsers({ page: 1, page_size: 100 }) : Promise.resolve({ items: [], total: 0, page: 1, page_size: 100 }),
      ]);
      setRecords(approvalResponse.items);
      setCandidates(candidateResponse.items);
      setApprovers(userResponse.items.filter((item) => ['admin', 'hrbp', 'manager'].includes(item.role)));
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [includeAll, decisionFilter, canSubmitApproval]);

  useEffect(() => {
    setSelection((current) => {
      if (current?.kind === 'approval' && records.some((item) => item.id === current.id)) {
        return current;
      }
      if (current?.kind === 'candidate' && candidates.some((item) => item.recommendation_id === current.id)) {
        return current;
      }
      const actionableApproval = records.find(
        (item) => item.decision === 'pending' && item.is_current_step && (item.approver_id === user?.id || user?.role === 'admin'),
      );
      if (actionableApproval) {
        return { kind: 'approval', id: actionableApproval.id };
      }
      if (candidates[0]) {
        return { kind: 'candidate', id: candidates[0].recommendation_id };
      }
      if (records[0]) {
        return { kind: 'approval', id: records[0].id };
      }
      return null;
    });
  }, [records, candidates, user?.id, user?.role]);

  const selectedCandidate = useMemo(
    () => (selection?.kind === 'candidate' ? candidates.find((item) => item.recommendation_id === selection.id) ?? null : null),
    [selection, candidates],
  );
  const selectedApproval = useMemo(
    () => (selection?.kind === 'approval' ? records.find((item) => item.id === selection.id) ?? null : null),
    [selection, records],
  );
  const selectedApprovalCanAct = Boolean(
    selectedApproval &&
      selectedApproval.decision === 'pending' &&
      selectedApproval.is_current_step &&
      (selectedApproval.approver_id === user?.id || user?.role === 'admin'),
  );

  const selectedDepartmentApprovers = useMemo(() => {
    if (!selectedCandidate) {
      return [];
    }
    return approvers.filter((candidate) => candidate.role === 'admin' || candidate.departments.some((item) => item.name === selectedCandidate.department));
  }, [approvers, selectedCandidate]);

  useEffect(() => {
    if (selectedCandidate) {
      const routeEmails = extractRouteEmails(selectedCandidate.route_preview);
      const nextIds = routeEmails
        .map((email) => selectedDepartmentApprovers.find((item) => item.email.toLowerCase() === email)?.id ?? '')
        .filter(Boolean);
      setRouteDraftApproverIds(nextIds.length ? nextIds : selectedDepartmentApprovers[0] ? [selectedDepartmentApprovers[0].id] : ['']);
      setDecisionComment('');
      setActionMode('approved');
      setDeferMode('time');
      setDeferDate('');
      setDeferScore('');
      return;
    }

    if (selectedApproval) {
      setDecisionComment(selectedApproval.comment ?? '');
      if (selectedApproval.decision === 'deferred') {
        setActionMode('deferred');
      } else if (selectedApproval.decision === 'rejected') {
        setActionMode('rejected');
      } else {
        setActionMode('approved');
      }
      if (selectedApproval.defer_until) {
        setDeferMode('time');
        setDeferDate(selectedApproval.defer_until.slice(0, 10));
      } else {
        setDeferDate('');
      }
      if (selectedApproval.defer_target_score != null) {
        setDeferMode('score');
        setDeferScore(String(selectedApproval.defer_target_score));
      } else {
        setDeferScore('');
      }
    }
  }, [selectedCandidate, selectedApproval, selectedDepartmentApprovers]);

  const pendingCount = useMemo(() => records.filter((item) => item.decision === 'pending').length, [records]);
  const actionableCount = useMemo(
    () =>
      records.filter(
        (item) =>
          item.decision === 'pending' &&
          item.is_current_step &&
          (item.approver_id === user?.id || user?.role === 'admin'),
      ).length,
    [records, user?.id, user?.role],
  );
  const deferredCount = useMemo(() => records.filter((item) => item.recommendation_status === 'deferred').length, [records]);
  const candidateCount = useMemo(
    () =>
      candidates.filter((item) =>
        ['recommended', 'adjusted', 'rejected', 'deferred', 'pending_approval'].includes(item.recommendation_status),
      ).length,
    [candidates],
  );

  const approvalRows = useMemo(
    () =>
      records.map((item) => ({
        id: item.id,
        employeeName: item.employee_name,
        department: item.department,
        aiLevel: item.ai_level,
        cycleName: item.cycle_name,
        recommendedIncrease: formatPercent(item.final_adjustment_ratio),
        approver: item.approver_email,
        status: item.decision,
        recommendationStatus: formatRecommendationStatus(item.recommendation_status),
        stepName: `${item.step_order}. ${formatStepName(item.step_name)}`,
        isCurrentStep: item.is_current_step,
        comment: item.comment ?? '',
        deferSummary: buildDeferSummary(item),
        canAct: item.decision === 'pending' && item.is_current_step && (item.approver_id === user?.id || user?.role === 'admin'),
      })),
    [records, user?.id, user?.role],
  );

  function updateRouteDraft(index: number, approverId: string) {
    setRouteDraftApproverIds((current) => current.map((item, itemIndex) => (itemIndex === index ? approverId : item)));
  }

  function addRouteDraftStep() {
    setRouteDraftApproverIds((current) => [...current, selectedDepartmentApprovers[0]?.id ?? '']);
  }

  function removeRouteDraftStep(index: number) {
    setRouteDraftApproverIds((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  async function handleSubmitCandidate(recommendationId: string) {
    setIsSubmittingCandidateId(recommendationId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await submitDefaultApproval(recommendationId);
      setSuccessMessage('调薪建议已进入默认审批流。');
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmittingCandidateId(null);
    }
  }

  async function handleSaveRoute() {
    if (!selectedCandidate) {
      return;
    }
    const cleanedIds = routeDraftApproverIds.map((item) => item.trim()).filter(Boolean);
    if (!cleanedIds.length) {
      setErrorMessage('请至少保留一个审批节点。');
      return;
    }
    if (new Set(cleanedIds).size !== cleanedIds.length) {
      setErrorMessage('审批路线里不能重复选择同一个审批人。');
      return;
    }
    const selectedUsers = cleanedIds
      .map((approverId) => selectedDepartmentApprovers.find((item) => item.id === approverId) ?? null)
      .filter((item): item is UserProfile => item !== null);
    if (selectedUsers.length !== cleanedIds.length) {
      setErrorMessage('审批路线里存在无效审批人，请重新选择。');
      return;
    }

    const steps: ApprovalStepPayload[] = selectedUsers.map((approver, index) => ({
      step_name: buildStepName(approver.role, index, selectedUsers.length),
      approver_id: approver.id,
      comment: `等待 ${approver.email} 处理审批。`,
    }));

    setEditingRecommendationId(selectedCandidate.recommendation_id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await updateApprovalRoute({
        recommendationId: selectedCandidate.recommendation_id,
        steps,
      });
      setSuccessMessage('审批路线已更新。');
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setEditingRecommendationId(null);
    }
  }

  async function handleSubmitApprovalDecision() {
    if (!selectedApproval) {
      return;
    }
    if (!selectedApproval.is_current_step || !(selectedApproval.approver_id === user?.id || user?.role === 'admin')) {
      setErrorMessage('当前节点还不能由你处理。');
      return;
    }

    setProcessingApprovalId(selectedApproval.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      if (actionMode === 'approved' || actionMode === 'rejected') {
        if (actionMode === 'rejected' && !decisionComment.trim()) {
          throw new Error('驳回时必须填写原因。');
        }
        await decideApproval({
          approvalId: selectedApproval.id,
          decision: actionMode,
          comment: decisionComment.trim() || undefined,
        });
        setSuccessMessage(actionMode === 'approved' ? '审批已通过。' : '审批已驳回。');
      } else {
        if (!decisionComment.trim()) {
          throw new Error('暂缓时必须填写原因。');
        }
        if (deferMode === 'time') {
          if (!deferDate) {
            throw new Error('请填写暂缓截止日期。');
          }
          await deferApproval({
            approvalId: selectedApproval.id,
            comment: decisionComment.trim(),
            deferUntil: new Date(`${deferDate}T23:59:59`).toISOString(),
          });
        } else {
          const parsedScore = Number(deferScore);
          if (Number.isNaN(parsedScore) || parsedScore < 0 || parsedScore > 100) {
            throw new Error('达标分数必须是 0 到 100 之间的数字。');
          }
          await deferApproval({
            approvalId: selectedApproval.id,
            comment: decisionComment.trim(),
            deferTargetScore: parsedScore,
          });
        }
        setSuccessMessage('该审批已暂缓，条件已保存。');
      }
      await loadData();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : resolveError(error));
    } finally {
      setProcessingApprovalId(null);
    }
  }

  return (
    <AppShell
      title="调薪审批中心"
      description="统一处理调薪建议发起、审批流转、暂缓，以及审批路线修改。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">
            返回工作台
          </Link>
          <Link className="action-primary" to="/salary-simulator">
            查看调薪模拟
          </Link>
        </>
      }
    >
      <section className="metric-strip animate-fade-up">
        {[
          [String(candidateCount), '待发起审批', '已生成调薪建议，但还未完成最终审批的记录。'],
          [String(actionableCount), '待我处理', '当前轮到你处理的审批节点数量。'],
          [String(pendingCount), '审批处理中', '仍处于待处理状态的审批节点数量。'],
          [String(deferredCount), '暂缓中', '已经设置暂缓条件、等待后续重新发起的调薪建议。'],
        ].map(([value, label, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[28px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-4" style={{ borderColor: 'var(--color-border)' }}>
          <div>
            <p className="eyebrow">筛选与范围</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">审批工作台</h2>
            <p className="mt-2 text-sm leading-6 text-steel">左侧浏览待处理建议和审批节点，右侧在同一页面完成修改路线、通过、驳回或暂缓。</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {user?.role === 'admin' || user?.role === 'hrbp' ? (
              <label className="flex items-center gap-2 text-sm text-steel">
                <input checked={includeAll} onChange={(event) => setIncludeAll(event.target.checked)} type="checkbox" />
                查看可见范围内全部审批记录
              </label>
            ) : null}
            <select className="toolbar-input" onChange={(event) => setDecisionFilter(event.target.value as typeof decisionFilter)} value={decisionFilter}>
              <option value="pending">仅看待处理</option>
              <option value="approved">仅看已通过</option>
              <option value="rejected">仅看已驳回</option>
              <option value="deferred">仅看已暂缓</option>
              <option value="all">查看全部</option>
            </select>
          </div>
        </div>
        {errorMessage ? <p className="mt-4 text-sm text-[var(--color-danger)]">{errorMessage}</p> : null}
        {successMessage ? <p className="mt-4 text-sm text-[var(--color-success)]">{successMessage}</p> : null}
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_420px]">
        <div className="grid gap-6">
          {canSubmitApproval ? (
            <section className="surface animate-fade-up px-6 py-6 lg:px-7">
              <div className="section-head">
                <div>
                  <p className="eyebrow">候选建议</p>
                  <h2 className="section-title">待处理的调薪建议</h2>
                </div>
                <span className="text-sm text-steel">{candidates.length} 条记录</span>
              </div>
              <div className="grid gap-3">
                {candidates.length ? (
                  candidates.map((item) => {
                    const isSelected = selection?.kind === 'candidate' && selection.id === item.recommendation_id;
                    return (
                      <button
                        key={item.recommendation_id}
                        className="surface-subtle px-4 py-4 text-left transition hover:border-[var(--color-primary-border)]"
                        onClick={() => setSelection({ kind: 'candidate', id: item.recommendation_id })}
                        style={{
                          borderColor: isSelected ? 'var(--color-primary)' : undefined,
                          background: isSelected ? 'var(--color-primary-light)' : undefined,
                        }}
                        type="button"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="font-medium text-ink">{item.employee_name}</div>
                            <div className="mt-1 text-xs text-steel">
                              {item.department} / {item.cycle_name}
                            </div>
                          </div>
                          <span className="status-pill" style={{ background: 'var(--color-info-bg)', color: 'var(--color-info)' }}>
                            {formatRecommendationStatus(item.recommendation_status)}
                          </span>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                          <div>
                            <div className="text-xs text-steel">当前薪资</div>
                            <div className="mt-1 font-medium text-ink">{formatCurrency(item.current_salary)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-steel">建议薪资</div>
                            <div className="mt-1 font-medium text-ink">{formatCurrency(item.recommended_salary)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-steel">建议涨幅</div>
                            <div className="mt-1 font-medium text-ink">{formatPercent(item.final_adjustment_ratio)}</div>
                          </div>
                        </div>
                        {item.route_edit_error ? (
                          <div className="mt-3 text-xs text-[var(--color-warning)]">{item.route_edit_error}</div>
                        ) : null}
                      </button>
                    );
                  })
                ) : (
                  <div className="rounded-[10px] border border-dashed border-[var(--color-border)] bg-[var(--color-bg-subtle)] px-4 py-5 text-sm text-steel">
                    当前没有待处理的调薪建议。
                  </div>
                )}
              </div>
            </section>
          ) : null}

          <ApprovalTable
            onSelect={(approvalId) => setSelection({ kind: 'approval', id: approvalId })}
            rows={approvalRows}
            selectedId={selection?.kind === 'approval' ? selection.id : null}
          />
        </div>

        <aside className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ alignSelf: 'start', position: 'sticky', top: 20 }}>
          <div className="section-head">
            <div>
              <p className="eyebrow">明细工作区</p>
              <h2 className="section-title">审批与路线设置</h2>
            </div>
          </div>

          {selectedCandidate ? (
            <div className="grid gap-5">
              <div>
                <div className="text-lg font-semibold text-ink">{selectedCandidate.employee_name}</div>
                <div className="mt-1 text-sm text-steel">
                  {selectedCandidate.department} / {selectedCandidate.cycle_name}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-xs text-steel">当前薪资</div>
                  <div className="mt-1 font-medium text-ink">{formatCurrency(selectedCandidate.current_salary)}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">建议薪资</div>
                  <div className="mt-1 font-medium text-ink">{formatCurrency(selectedCandidate.recommended_salary)}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">建议涨幅</div>
                  <div className="mt-1 font-medium text-ink">{formatPercent(selectedCandidate.final_adjustment_ratio)}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">当前状态</div>
                  <div className="mt-1 font-medium text-ink">{formatRecommendationStatus(selectedCandidate.recommendation_status)}</div>
                </div>
              </div>

              {buildDeferSummary(selectedCandidate) ? (
                <div className="rounded-[10px] bg-[var(--color-bg-subtle)] px-4 py-3 text-sm leading-6 text-steel">
                  当前暂缓条件：{buildDeferSummary(selectedCandidate)}
                </div>
              ) : null}

              <div className="grid gap-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-ink">审批路线设置</div>
                    <div className="mt-1 text-xs text-steel">在页面内调整审批顺序和审批人，不再通过弹窗修改。</div>
                  </div>
                  <button className="action-secondary px-4 py-2 text-xs" onClick={addRouteDraftStep} type="button">
                    新增节点
                  </button>
                </div>

                {routeDraftApproverIds.map((approverId, index) => (
                  <div key={`${selection?.kind}-${selection?.id}-${index}`} className="surface-subtle px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-ink">节点 {index + 1}</div>
                      <button
                        className="action-danger px-3 py-2 text-xs"
                        disabled={routeDraftApproverIds.length <= 1}
                        onClick={() => removeRouteDraftStep(index)}
                        type="button"
                      >
                        移除
                      </button>
                    </div>
                    <select className="toolbar-input mt-3 w-full" onChange={(event) => updateRouteDraft(index, event.target.value)} value={approverId}>
                      <option value="">请选择审批人</option>
                      {selectedDepartmentApprovers.map((approver) => (
                        <option key={approver.id} value={approver.id}>
                          {approver.email} / {approver.role}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {selectedCandidate.route_edit_error ? (
                <div className="rounded-[10px] bg-[var(--color-warning-bg)] px-4 py-3 text-sm leading-6 text-[var(--color-warning)]">
                  {selectedCandidate.route_edit_error}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <button
                  className="action-primary"
                  disabled={!selectedCandidate.can_edit_route || editingRecommendationId === selectedCandidate.recommendation_id}
                  onClick={() => void handleSaveRoute()}
                  type="button"
                >
                  {editingRecommendationId === selectedCandidate.recommendation_id ? '保存中...' : '保存审批路线'}
                </button>
                <button
                  className="action-secondary"
                  disabled={isSubmittingCandidateId === selectedCandidate.recommendation_id}
                  onClick={() => void handleSubmitCandidate(selectedCandidate.recommendation_id)}
                  type="button"
                >
                  {isSubmittingCandidateId === selectedCandidate.recommendation_id ? '提交中...' : '按默认路线发起审批'}
                </button>
                <Link className="chip-button" to={`/employees/${selectedCandidate.employee_id}`}>
                  查看员工详情
                </Link>
              </div>
            </div>
          ) : null}

          {selectedApproval ? (
            <div className="grid gap-5">
              <div>
                <div className="text-lg font-semibold text-ink">{selectedApproval.employee_name}</div>
                <div className="mt-1 text-sm text-steel">
                  {selectedApproval.department} / {selectedApproval.cycle_name}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-xs text-steel">审批节点</div>
                  <div className="mt-1 font-medium text-ink">{formatStepName(selectedApproval.step_name)}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">审批人</div>
                  <div className="mt-1 font-medium text-ink">{selectedApproval.approver_email}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">建议状态</div>
                  <div className="mt-1 font-medium text-ink">{formatRecommendationStatus(selectedApproval.recommendation_status)}</div>
                </div>
                <div>
                  <div className="text-xs text-steel">建议涨幅</div>
                  <div className="mt-1 font-medium text-ink">{formatPercent(selectedApproval.final_adjustment_ratio)}</div>
                </div>
              </div>

              <div className="grid gap-2">
                <div className="text-sm font-semibold text-ink">审批动作</div>
                <div className="flex flex-wrap gap-2">
                  {([
                    ['approved', '通过'],
                    ['rejected', '驳回'],
                    ['deferred', '暂缓'],
                  ] as Array<[ActionMode, string]>).map(([mode, label]) => (
                    <button
                      key={mode}
                      className={actionMode === mode ? 'action-primary px-4 py-2 text-xs' : 'action-secondary px-4 py-2 text-xs'}
                      onClick={() => setActionMode(mode)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-ink">{actionMode === 'approved' ? '审批备注' : actionMode === 'rejected' ? '驳回原因' : '暂缓原因'}</div>
                <textarea
                  className="toolbar-textarea mt-3 w-full"
                  onChange={(event) => setDecisionComment(event.target.value)}
                  placeholder={actionMode === 'approved' ? '可填写审批备注' : actionMode === 'rejected' ? '请填写驳回原因' : '请填写暂缓原因'}
                  value={decisionComment}
                />
              </div>

              {actionMode === 'deferred' ? (
                <div className="grid gap-3">
                  <div className="text-sm font-semibold text-ink">暂缓条件</div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className={deferMode === 'time' ? 'action-primary px-4 py-2 text-xs' : 'action-secondary px-4 py-2 text-xs'}
                      onClick={() => setDeferMode('time')}
                      type="button"
                    >
                      按时间
                    </button>
                    <button
                      className={deferMode === 'score' ? 'action-primary px-4 py-2 text-xs' : 'action-secondary px-4 py-2 text-xs'}
                      onClick={() => setDeferMode('score')}
                      type="button"
                    >
                      按达标分数
                    </button>
                  </div>
                  {deferMode === 'time' ? (
                    <input className="toolbar-input w-full" onChange={(event) => setDeferDate(event.target.value)} type="date" value={deferDate} />
                  ) : (
                    <input className="toolbar-input w-full" max={100} min={0} onChange={(event) => setDeferScore(event.target.value)} placeholder="请输入 0-100 的达标分数" type="number" value={deferScore} />
                  )}
                </div>
              ) : null}

              {selectedApprovalCanAct ? (
                <button
                  className="action-primary"
                  disabled={processingApprovalId === selectedApproval.id}
                  onClick={() => void handleSubmitApprovalDecision()}
                  type="button"
                >
                  {processingApprovalId === selectedApproval.id ? '处理中...' : actionMode === 'approved' ? '提交通过' : actionMode === 'rejected' ? '提交驳回' : '提交暂缓'}
                </button>
              ) : (
                <div className="rounded-[10px] bg-[var(--color-bg-subtle)] px-4 py-3 text-sm leading-6 text-steel">
                  当前节点仅支持查看，尚未轮到你处理或该节点已完成。
                </div>
              )}
            </div>
          ) : null}

          {!selectedCandidate && !selectedApproval ? (
            <div className="rounded-[10px] border border-dashed border-[var(--color-border)] bg-[var(--color-bg-subtle)] px-4 py-5 text-sm text-steel">
              从左侧选择一条调薪建议或审批记录后，这里会显示对应的详细处理面板。
            </div>
          ) : null}
        </aside>
      </section>
    </AppShell>
  );
}
