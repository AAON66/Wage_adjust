import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { DistributionChart } from '../components/dashboard/DistributionChart';
import { HeatmapChart } from '../components/dashboard/HeatmapChart';
import { OverviewCards } from '../components/dashboard/OverviewCards';
import { AppShell } from '../components/layout/AppShell';
import { fetchDashboardSnapshot } from '../services/dashboardService';
import type { DashboardSnapshotResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载看板洞察失败。';
  }
  return '加载看板洞察失败。';
}

function colorForLabel(label: string): string {
  if (label.includes('五级') || label.includes('2.0x+') || label.includes('2.0x 以上')) return 'bg-emerald-500';
  if (label.includes('四级') || label.includes('1.5x')) return 'bg-[#2d5cff]';
  if (label.includes('三级') || label.includes('1.0x')) return 'bg-sky-400';
  if (label.includes('二级')) return 'bg-sky-200';
  return 'bg-slate-300';
}

function localizeOverviewLabel(label: string): string {
  return {
    'Employees in cycle': '周期员工数',
    'Employees in scope': '纳入范围员工数',
    'Budget used': '已用预算',
    'Average increase': '平均涨幅',
    'Approved recommendations': '已审批建议数',
    'High potential': '高潜人才',
    'Review backlog': '待复核项',
    '覆盖员工数': '覆盖员工数',
    '纳入范围员工数': '纳入范围员工数',
  }[label] ?? label;
}

function localizeOverviewNote(note: string): string {
  return {
    'Employees with submissions in the selected cycle.': '当前所选周期中已进入流程的员工数。',
    'Distinct employees covered by current submission scope.': '当前提交范围内去重后的员工总数。',
    'Total recommended salary amount compared with available cycle budget.': '建议调薪总额与周期预算的当前对比。',
    'Average final adjustment ratio for available recommendations.': '当前建议方案的平均最终调整比例。',
    'Recommendations that have completed the approval workflow.': '已经完成审批流程的调薪建议数量。',
    'Evaluations at Level 4+, or overall score 85 and above.': 'AI 四级及以上，或综合得分达到 85 分及以上的员工数。',
    'Evaluations still waiting for review confirmation or calibration.': '仍待人工复核确认或校准处理的评估数量。',
  }[note] ?? note;
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

export function DashboardPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadDashboard() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await fetchDashboardSnapshot();
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
  }, []);

  const overviewItems = useMemo(
    () =>
      (snapshot?.overview.items ?? []).map((item) => ({
        ...item,
        label: localizeOverviewLabel(item.label),
        note: localizeOverviewNote(item.note),
      })),
    [snapshot],
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

  return (
    <AppShell
      title="组织洞察看板"
      description="以运营视角查看当前范围内的预算占用、能力分布、高潜画像和部门热度。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="rounded-full bg-[#2d5cff] px-5 py-2.5 text-sm font-medium text-white shadow-float" to="/import-center">打开导入中心</Link>
        </>
      }
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载组织看板...</p> : null}
      <OverviewCards items={overviewItems} />
      <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <HeatmapChart cells={snapshot?.heatmap.items ?? []} />
        <DistributionChart items={aiLevelItems} title="AI 等级分布" />
      </section>
      <DistributionChart items={roiItems} title="预估 ROI 区间分布" />
    </AppShell>
  );
}
