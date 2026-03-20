import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { DistributionChart } from '../components/dashboard/DistributionChart';
import { HeatmapChart } from '../components/dashboard/HeatmapChart';
import { OverviewCards } from '../components/dashboard/OverviewCards';
import { fetchDashboardSnapshot } from '../services/dashboardService';
import type { DashboardSnapshotResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      'Failed to load dashboard insights.';
  }
  return 'Failed to load dashboard insights.';
}

function colorForLabel(label: string): string {
  if (label.includes('Level 5') || label.includes('2.0x+')) return 'bg-emerald-500';
  if (label.includes('Level 4') || label.includes('1.5x')) return 'bg-ink';
  if (label.includes('Level 3') || label.includes('1.0x')) return 'bg-amber-400';
  if (label.includes('Level 2')) return 'bg-amber-200';
  return 'bg-slate-300';
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

  const aiLevelItems = useMemo(
    () =>
      (snapshot?.ai_level_distribution.items ?? []).map((item) => ({
        ...item,
        colorClass: colorForLabel(item.label),
      })),
    [snapshot],
  );

  const roiItems = useMemo(
    () =>
      (snapshot?.roi_distribution.items ?? []).map((item) => ({
        ...item,
        colorClass: colorForLabel(item.label),
      })),
    [snapshot],
  );

  return (
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-start justify-between gap-4 rounded-[32px] bg-white p-6 shadow-panel">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Dashboard</p>
            <h1 className="mt-2 text-4xl font-bold">Organization insights board</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              This page now reads the live dashboard APIs for overview metrics, AI distribution, department density, and estimated ROI bands.
            </p>
          </div>
          <div className="flex gap-3">
            <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/workspace">
              Back to workspace
            </Link>
            <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/import-center">
              Open import center
            </Link>
          </div>
        </header>

        {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{errorMessage}</p> : null}
        {isLoading ? <p className="text-sm text-slate-500">Loading dashboard...</p> : null}

        <OverviewCards items={snapshot?.overview.items ?? []} />

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <HeatmapChart cells={snapshot?.heatmap.items ?? []} />
          <DistributionChart items={aiLevelItems} title="AI level distribution" />
        </section>

        <DistributionChart items={roiItems} title="Estimated ROI conversion bands" />
      </div>
    </main>
  );
}
