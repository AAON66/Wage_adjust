import type React from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { CreateCycleForm } from '../components/cycle/CreateCycleForm';
import { AppShell } from '../components/layout/AppShell';
import { archiveCycle, createCycle, deleteCycle, fetchCycles, publishCycle, updateCycle } from '../services/cycleService';
import { fetchDepartments } from '../services/userAdminService';
import type { CycleCreatePayload, CycleDepartmentBudgetRecord, CycleRecord, DepartmentRecord } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '评估周期操作失败。'
    );
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

function statusTone(status: string): React.CSSProperties {
  return (
    {
      draft: { background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' },
      collecting: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
      published: { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
      archived: { background: 'var(--color-danger-bg)', color: 'var(--color-danger)' },
    } as Record<string, React.CSSProperties>
  )[status] ?? { background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' };
}

function toFormValues(cycle: CycleRecord): CycleCreatePayload {
  return {
    name: cycle.name,
    review_period: cycle.review_period,
    budget_amount: cycle.budget_amount,
    status: cycle.status === 'archived' ? 'draft' : cycle.status,
    department_budgets: cycle.department_budgets.map((item) => ({
      department_id: item.department_id,
      budget_amount: item.budget_amount,
    })),
  };
}

function summarizeDepartmentBudgets(items: CycleDepartmentBudgetRecord[], departments: DepartmentRecord[]): string {
  if (!items.length) {
    return '未单独设置部门预算，系统会按当前启用部门自动平分预算。';
  }

  const activeDepartmentCount = departments.filter((item) => item.status === 'active').length;
  const explicitNames = items.map((item) => `${item.department_name}（${item.budget_amount}）`).join('、');
  if (items.length >= activeDepartmentCount && activeDepartmentCount > 0) {
    return `已逐部门设置预算：${explicitNames}`;
  }
  return `已指定预算：${explicitNames}。其余部门将平分剩余预算。`;
}

export function CreateCyclePage() {
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<CycleRecord | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [workingCycleId, setWorkingCycleId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadPageData() {
    setIsRefreshing(true);
    try {
      const [cycleResponse, departmentResponse] = await Promise.all([fetchCycles(), fetchDepartments()]);
      setCycles(cycleResponse.items);
      setDepartments(departmentResponse.items);
      setSelectedCycle((current) => {
        if (!current) {
          return null;
        }
        return cycleResponse.items.find((item) => item.id === current.id) ?? null;
      });
    } catch (error) {
      setCycles([]);
      setDepartments([]);
      setErrorMessage(resolveError(error));
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void loadPageData();
  }, []);

  const stats = useMemo(
    () => ({
      total: cycles.length,
      active: cycles.filter((item) => item.status !== 'archived').length,
      published: cycles.filter((item) => item.status === 'published').length,
      archived: cycles.filter((item) => item.status === 'archived').length,
    }),
    [cycles],
  );

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
      await loadPageData();
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
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingCycleId(null);
    }
  }

  async function handleArchive(cycle: CycleRecord) {
    if (!window.confirm(`确认下架评估周期“${cycle.name}”吗？下架后它将不再参与后续流转。`)) {
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
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingCycleId(null);
    }
  }

  async function handleDelete(cycle: CycleRecord) {
    if (!window.confirm(`确认删除评估周期“${cycle.name}”吗？仅无员工提交数据的周期允许删除，删除后无法恢复。`)) {
      return;
    }

    setWorkingCycleId(cycle.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await deleteCycle(cycle.id);
      setSuccessMessage(`周期“${cycle.name}”已删除。`);
      if (selectedCycle?.id === cycle.id) {
        setSelectedCycle(null);
      }
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingCycleId(null);
    }
  }

  return (
    <AppShell
      title="评估周期管理"
      description="新建、编辑、发布和删除评估周期，并为各部门设置独立预算分配规则。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">
            返回工作台
          </Link>
          <Link className="chip-button" to="/employees">
            员工列表
          </Link>
          <button className="action-secondary" onClick={() => void loadPageData()} type="button">
            {isRefreshing ? '刷新中...' : '刷新周期'}
          </button>
        </>
      }
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['周期总数', String(stats.total), '当前系统中已经建立的评估周期数量。'],
          ['可用周期', String(stats.active), '未下架、仍可参与业务流转的周期。'],
          ['已发布', String(stats.published), '已经正式生效、可用于评估与调薪的周期。'],
          ['已下架', String(stats.archived), '仅保留历史记录、不再继续使用的周期。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      {errorMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}
      {successMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-success)' }}>
          {successMessage}
        </p>
      ) : null}

      <section className="grid gap-5 lg:grid-cols-[0.96fr_1.04fr]">
        <section className="surface" style={{ padding: '20px 24px' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
            <p className="eyebrow">周期配置</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">{selectedCycle ? '编辑评估周期' : '新建评估周期'}</h2>
            <p className="mt-2 text-sm leading-6 text-steel">
              {selectedCycle
                ? '可以修改周期名称、总预算和部门分配规则。若未单独设置某部门预算，系统会自动把剩余预算平分到未设置部门。'
                : '创建新周期时可以直接配置部门预算；如果暂时不配置，系统会按启用中的部门自动平分总预算。'}
            </p>
            <p className="mt-2 text-sm leading-6 text-steel">右侧周期卡片里的“设置部门预算”按钮，就是进入该周期预算配置的快捷入口。</p>
          </div>
          <div className="mt-5">
            <CreateCycleForm
              departments={departments}
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

        <section className="surface" style={{ padding: '20px 24px', animationDelay: '60ms' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              gap: 12,
              borderBottom: '1px solid var(--color-border)',
              paddingBottom: 12,
              marginBottom: 16,
            }}
          >
            <div>
              <p className="eyebrow">已有周期</p>
              <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">现有评估周期</h2>
              <p className="mt-2 text-sm leading-6 text-steel">支持编辑、发布、下架和删除，并可查看当前部门预算分配规则。</p>
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
                    <div className="max-w-[75%]">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-ink">{cycle.name}</h3>
                        <span className="status-pill" style={statusTone(cycle.status)}>
                          {formatStatus(cycle.status)}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-steel">评估周期：{cycle.review_period}</p>
                      <p className="mt-1 text-sm text-steel">总预算：{cycle.budget_amount}</p>
                      <p className="mt-1 text-sm text-steel">
                        更新时间：
                        {new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(cycle.updated_at))}
                      </p>
                      <p className="mt-3 text-sm leading-6 text-steel">{summarizeDepartmentBudgets(cycle.department_budgets, departments)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="action-primary px-4 py-2 text-xs"
                        disabled={isArchived}
                        onClick={() => {
                          setSelectedCycle(cycle);
                          setErrorMessage(null);
                          setSuccessMessage(`正在编辑“${cycle.name}”的部门预算。`);
                        }}
                        type="button"
                      >
                        设置部门预算
                      </button>
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
                        编辑周期
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
                      <button
                        className="action-danger px-4 py-2 text-xs"
                        disabled={isBusy}
                        onClick={() => void handleDelete(cycle)}
                        type="button"
                      >
                        {isBusy ? '处理中...' : '删除周期'}
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
