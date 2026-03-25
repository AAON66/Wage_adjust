import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ActionSummaryPanel } from '../components/dashboard/ActionSummaryPanel';
import { DepartmentInsightTable } from '../components/dashboard/DepartmentInsightTable';
import { DistributionChart } from '../components/dashboard/DistributionChart';
import { HeatmapChart } from '../components/dashboard/HeatmapChart';
import { OverviewCards } from '../components/dashboard/OverviewCards';
import { TalentSpotlightPanel } from '../components/dashboard/TalentSpotlightPanel';
import { AppShell } from '../components/layout/AppShell';
import { fetchCycles } from '../services/cycleService';
import { fetchDashboardSnapshot } from '../services/dashboardService';
import type { CycleRecord, DashboardSnapshotResponse } from '../types/api';
import { formatCycleStatus } from '../utils/statusText';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载组织洞察看板失败。'
    );
  }
  return '加载组织洞察看板失败。';
}

function localizeDistributionLabel(label: string): string {
  return {
    'Level 1': '一级',
    'Level 2': '二级',
    'Level 3': '三级',
    'Level 4': '四级',
    'Level 5': '五级',
    'Under 1.0x': '1.0x 以下',
    '1.0x - 1.5x': '1.0x - 1.5x',
    '1.5x - 2.0x': '1.5x - 2.0x',
    '2.0x+': '2.0x 以上',
  }[label] ?? label;
}

function colorForLabel(label: string): string {
  if (label.includes('五级') || label.includes('2.0x')) return 'bg-emerald-500';
  if (label.includes('四级') || label.includes('1.5x')) return 'bg-[#2d5cff]';
  if (label.includes('三级') || label.includes('1.0x')) return 'bg-sky-400';
  if (label.includes('二级')) return 'bg-sky-200';
  return 'bg-slate-300';
}

function formatCurrency(value: string | null | undefined): string {
  if (!value) {
    return '--';
  }

  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function buildCycleHeadline(snapshot: DashboardSnapshotResponse | null, cycle: CycleRecord | null): string {
  const summary = snapshot?.cycle_summary;
  if (summary?.cycle_name) {
    return summary.cycle_name;
  }
  if (cycle?.name) {
    return cycle.name;
  }
  return '全部可见周期';
}

export function DashboardPage() {
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [snapshot, setSnapshot] = useState<DashboardSnapshotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCycles() {
      try {
        const response = await fetchCycles();
        if (cancelled) {
          return;
        }

        setCycles(response.items);
        setSelectedCycleId((current) => {
          if (current || !response.items.length) {
            return current;
          }

          const preferredCycle =
            response.items.find((item) => item.status === 'published') ??
            response.items.find((item) => item.status === 'collecting') ??
            response.items[0];

          return preferredCycle?.id ?? '';
        });
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      }
    }

    void loadCycles();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await fetchDashboardSnapshot(selectedCycleId || undefined);
        if (!cancelled) {
          setSnapshot(response);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [selectedCycleId]);

  const selectedCycle = useMemo(
    () => cycles.find((item) => item.id === selectedCycleId) ?? null,
    [cycles, selectedCycleId],
  );

  const aiLevelItems = useMemo(
    () =>
      (snapshot?.ai_level_distribution.items ?? []).map((item) => {
        const label = localizeDistributionLabel(item.label);
        return {
          ...item,
          label,
          colorClass: colorForLabel(label),
        };
      }),
    [snapshot],
  );

  const roiItems = useMemo(
    () =>
      (snapshot?.roi_distribution.items ?? []).map((item) => {
        const label = localizeDistributionLabel(item.label);
        return {
          ...item,
          label,
          colorClass: colorForLabel(label),
        };
      }),
    [snapshot],
  );

  const cycleSummary = snapshot?.cycle_summary ?? null;
  const selectedCycleName = buildCycleHeadline(snapshot, selectedCycle);
  const reviewPeriod = cycleSummary?.review_period || selectedCycle?.review_period || '当前可见周期';
  const cycleStatus = formatCycleStatus(cycleSummary?.status ?? selectedCycle?.status);
  const budgetAmount = formatCurrency(cycleSummary?.budget_amount ?? selectedCycle?.budget_amount);
  const topTalent = snapshot?.top_talents?.[0] ?? null;
  const firstAction = snapshot?.action_items?.[0] ?? null;
  const departmentCount = snapshot?.department_insights.length ?? 0;

  return (
    <AppShell
      title="组织洞察看板"
      description="围绕预算、评估、审批和人才分布查看当前组织状态，帮助管理端快速定位重点部门与关键员工。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">
            返回工作台
          </Link>
          <Link className="chip-button" to="/user-admin">
            部门管理
          </Link>
          <Link className="action-primary" to="/approvals">
            打开审批中心
          </Link>
        </>
      }
    >
      <section className="dashboard-hero animate-fade-up">
        <div className="dashboard-hero-copy">
          <p className="dashboard-kicker">组织驾驶舱</p>
          <h2 className="dashboard-hero-title">{selectedCycleName}</h2>
          <p className="dashboard-hero-desc">
            当前看板按评估周期聚合真实预算、审批与人才数据，优先帮助你判断哪里需要先复核、先审批、先补预算。
          </p>
          <div className="dashboard-hero-meta">
            <span className="dashboard-chip dashboard-chip-strong">{cycleStatus}</span>
            <span className="dashboard-chip">{reviewPeriod}</span>
            <span className="dashboard-chip">预算 {budgetAmount}</span>
          </div>
        </div>

        <div className="dashboard-hero-rail">
          <div className="dashboard-signal-card">
            <p className="dashboard-signal-label">重点动作</p>
            <p className="dashboard-signal-value">{firstAction?.value ?? '--'}</p>
            <p className="dashboard-signal-note">{firstAction?.title ?? '当前暂无待处理动作'}</p>
          </div>
          <div className="dashboard-signal-card">
            <p className="dashboard-signal-label">关注员工</p>
            <p className="dashboard-signal-value">{topTalent?.employee_name ?? '--'}</p>
            <p className="dashboard-signal-note">
              {topTalent ? `${topTalent.department} · 综合分 ${topTalent.overall_score.toFixed(1)}` : '当前暂无高优先级员工'}
            </p>
          </div>
          <div className="dashboard-signal-card">
            <p className="dashboard-signal-label">覆盖部门</p>
            <p className="dashboard-signal-value">{departmentCount}</p>
            <p className="dashboard-signal-note">已纳入当前视图的部门数量</p>
          </div>
        </div>
      </section>

      <section className="dashboard-toolbar surface-subtle animate-fade-up">
        <div>
          <p className="dashboard-toolbar-label">查看周期</p>
          <p className="dashboard-toolbar-note">切换周期后，看板会联动更新预算、分布与审批进度。</p>
        </div>
        <div className="dashboard-toolbar-control">
          <select className="toolbar-input w-full" onChange={(event) => setSelectedCycleId(event.target.value)} value={selectedCycleId}>
            <option value="">全部可见周期</option>
            {cycles.map((cycle) => (
              <option key={cycle.id} value={cycle.id}>
                {cycle.name}
              </option>
            ))}
          </select>
        </div>
      </section>

      {errorMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载组织洞察看板...</p> : null}

      <OverviewCards items={snapshot?.overview.items ?? []} />

      <section className="dashboard-stage-grid">
        <div className="dashboard-stage-main">
          <ActionSummaryPanel cycleSummary={cycleSummary} items={snapshot?.action_items ?? []} />
        </div>
        <div className="dashboard-stage-side">
          <TalentSpotlightPanel items={snapshot?.top_talents ?? []} />
        </div>
      </section>

      <section className="dashboard-analysis-grid">
        <div className="dashboard-analysis-primary">
          <HeatmapChart cells={snapshot?.heatmap.items ?? []} />
        </div>
        <div className="dashboard-analysis-secondary">
          <DistributionChart compact items={aiLevelItems} title="AI 等级分布" />
          <DistributionChart compact items={roiItems} title="预计 ROI 区间分布" />
        </div>
      </section>

      <DepartmentInsightTable rows={snapshot?.department_insights ?? []} />
    </AppShell>
  );
}
