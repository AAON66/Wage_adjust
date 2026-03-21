import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { CreateCycleForm } from '../components/cycle/CreateCycleForm';
import { AppShell } from '../components/layout/AppShell';
import { archiveCycle, createCycle, fetchCycles, publishCycle, updateCycle } from '../services/cycleService';
import type { CycleCreatePayload, CycleRecord } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '评估周期操作失败。';
  }
  return '评估周期操作失败。';
}

function formatStatus(status: string): string {
  return {
    draft: '草稿',
    collecting: '收集中',
    published: '已发布',
    archived: '已下架',
  }[status] ?? status;
}

function statusTone(status: string): string {
  return {
    draft: 'bg-slate-100 text-slate-600',
    collecting: 'bg-amber-50 text-amber-700',
    published: 'bg-emerald-50 text-emerald-700',
    archived: 'bg-rose-50 text-rose-600',
  }[status] ?? 'bg-slate-100 text-slate-600';
}

function toFormValues(cycle: CycleRecord): CycleCreatePayload {
  return {
    name: cycle.name,
    review_period: cycle.review_period,
    budget_amount: cycle.budget_amount,
    status: cycle.status === 'archived' ? 'draft' : cycle.status,
  };
}

export function CreateCyclePage() {
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<CycleRecord | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [workingCycleId, setWorkingCycleId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadCycles() {
    setIsRefreshing(true);
    try {
      const response = await fetchCycles();
      setCycles(response.items);
      setSelectedCycle((current) => {
        if (!current) return null;
        return response.items.find((item) => item.id === current.id) ?? null;
      });
    } catch {
      setCycles([]);
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void loadCycles();
  }, []);

  const stats = useMemo(() => {
    return {
      total: cycles.length,
      active: cycles.filter((item) => item.status !== 'archived').length,
      published: cycles.filter((item) => item.status === 'published').length,
      archived: cycles.filter((item) => item.status === 'archived').length,
    };
  }, [cycles]);

  async function handleSubmit(payload: CycleCreatePayload) {
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      if (selectedCycle) {
        await updateCycle(selectedCycle.id, payload);
        setSuccessMessage('评估周期已更新。');
      } else {
        await createCycle(payload);
        setSuccessMessage('评估周期已创建。');
      }
      setSelectedCycle(null);
      await loadCycles();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePublish(cycle: CycleRecord) {
    setWorkingCycleId(cycle.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await publishCycle(cycle.id);
      setSuccessMessage(`周期“${cycle.name}”已发布。`);
      await loadCycles();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingCycleId(null);
    }
  }

  async function handleArchive(cycle: CycleRecord) {
    if (!window.confirm(`确认下架评估周期“${cycle.name}”吗？下架后将不再作为可用周期继续流转。`)) {
      return;
    }
    setWorkingCycleId(cycle.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await archiveCycle(cycle.id);
      setSuccessMessage(`周期“${cycle.name}”已下架。`);
      if (selectedCycle?.id === cycle.id) {
        setSelectedCycle(null);
      }
      await loadCycles();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingCycleId(null);
    }
  }

  return (
    <AppShell
      title="评估周期管理"
      description="在同一页面里完成周期新建、编辑、发布和下架，保持评估节奏和预算范围可控。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="chip-button" to="/employees">员工列表</Link>
          <button className="action-secondary" onClick={() => void loadCycles()} type="button">{isRefreshing ? '刷新中...' : '刷新周期'}</button>
        </>
      }
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['周期总数', String(stats.total), '当前系统中已建立的评估周期数量。'],
          ['可用周期', String(stats.active), '未下架、仍可参与业务流转的周期。'],
          ['已发布', String(stats.published), '已经对评估流程正式生效的周期。'],
          ['已下架', String(stats.archived), '不再继续使用的历史周期。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm text-emerald-700">{successMessage}</p> : null}

      <section className="grid gap-5 lg:grid-cols-[0.96fr_1.04fr]">
        <section className="surface animate-fade-up px-6 py-6 lg:px-7">
          <div className="border-b border-[#e6eef9] pb-4">
            <p className="eyebrow">周期配置</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">{selectedCycle ? '编辑评估周期' : '新建评估周期'}</h2>
            <p className="mt-2 text-sm leading-6 text-steel">
              {selectedCycle
                ? '修改周期名称、评估时间和预算范围。已下架周期不可再编辑。'
                : '为后续员工评估、预算模拟和审批流创建统一的时间与预算范围。'}
            </p>
          </div>
          <div className="mt-5">
            <CreateCycleForm
              errorMessage={errorMessage}
              initialValues={selectedCycle ? toFormValues(selectedCycle) : undefined}
              isEditing={Boolean(selectedCycle)}
              isSubmitting={isSubmitting}
              onCancelEdit={() => {
                setSelectedCycle(null);
                setErrorMessage(null);
              }}
              onSubmit={handleSubmit}
            />
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '60ms' }}>
          <div className="flex items-end justify-between gap-3 border-b border-[#e6eef9] pb-4">
            <div>
              <p className="eyebrow">已有周期</p>
              <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">现有评估周期</h2>
              <p className="mt-2 text-sm leading-6 text-steel">支持直接编辑草稿或进行发布、下架管理。</p>
            </div>
            <p className="text-sm text-steel">共 {cycles.length} 个周期</p>
          </div>
          <div className="mt-5 space-y-3">
            {cycles.map((cycle) => {
              const isArchived = cycle.status === 'archived';
              const isPublished = cycle.status === 'published';
              const isBusy = workingCycleId === cycle.id;
              return (
                <article className="surface-subtle px-5 py-5" key={cycle.id}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-ink">{cycle.name}</h3>
                        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone(cycle.status)}`}>{formatStatus(cycle.status)}</span>
                      </div>
                      <p className="mt-3 text-sm text-steel">评估周期：{cycle.review_period}</p>
                      <p className="mt-1 text-sm text-steel">预算：{cycle.budget_amount}</p>
                      <p className="mt-1 text-sm text-steel">更新时间：{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(cycle.updated_at))}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="action-secondary px-4 py-2 text-xs"
                        disabled={isArchived}
                        onClick={() => {
                          setSelectedCycle(cycle);
                          setErrorMessage(null);
                          setSuccessMessage(null);
                        }}
                        type="button"
                      >
                        编辑
                      </button>
                      <button
                        className="action-primary px-4 py-2 text-xs"
                        disabled={isArchived || isPublished || isBusy}
                        onClick={() => void handlePublish(cycle)}
                        type="button"
                      >
                        {isBusy && !isPublished ? '处理中...' : '发布'}
                      </button>
                      <button
                        className="action-danger px-4 py-2 text-xs"
                        disabled={isArchived || isBusy}
                        onClick={() => void handleArchive(cycle)}
                        type="button"
                      >
                        {isBusy && !isArchived ? '处理中...' : '下架'}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
            {cycles.length === 0 ? <p className="text-sm text-steel">当前还没有周期数据。</p> : null}
          </div>
        </section>
      </section>
    </AppShell>
  );
}
