import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';

import { AILevelChart } from '../components/dashboard/AILevelChart';
import { ApprovalPipelineChart } from '../components/dashboard/ApprovalPipelineChart';
import { DepartmentInsightTable } from '../components/dashboard/DepartmentInsightTable';
import { KpiCards } from '../components/dashboard/KpiCards';
import { SalaryDistChart } from '../components/dashboard/SalaryDistChart';
import { AppShell } from '../components/layout/AppShell';
import { fetchCycles } from '../services/cycleService';
import {
  fetchAiLevelDistribution,
  fetchApprovalPipeline,
  fetchDashboardSnapshot,
  fetchSalaryDistribution,
} from '../services/dashboardService';
import type {
  CycleRecord,
  DashboardDepartmentInsight,
  DashboardDistributionItem,
} from '../types/api';

// D-11: employee 角色已在 ProtectedRoute (App.tsx:418) + require_roles (dashboard.py) 双重排除

export function DashboardPage() {
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');

  const [aiLevelData, setAiLevelData] = useState<DashboardDistributionItem[]>([]);
  const [salaryDistData, setSalaryDistData] = useState<DashboardDistributionItem[]>([]);
  const [approvalData, setApprovalData] = useState<DashboardDistributionItem[]>([]);
  const [departmentInsights, setDepartmentInsights] = useState<DashboardDepartmentInsight[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRedisUnavailable, setIsRedisUnavailable] = useState(false);

  // Load cycles on mount
  useEffect(() => {
    let cancelled = false;

    async function loadCycles() {
      try {
        const response = await fetchCycles();
        if (cancelled) return;

        setCycles(response.items);
        setSelectedCycleId((current) => {
          if (current || !response.items.length) return current;

          const preferredCycle =
            response.items.find((item) => item.status === 'published') ??
            response.items.find((item) => item.status === 'collecting') ??
            response.items[0];

          return preferredCycle?.id ?? '';
        });
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(
            axios.isAxiosError(error)
              ? (error.response?.data as { message?: string } | undefined)?.message ?? '加载周期列表失败。'
              : '加载周期列表失败。'
          );
        }
      }
    }

    void loadCycles();
    return () => { cancelled = true; };
  }, []);

  // Fetch chart data when cycle changes — reset all dependent state
  useEffect(() => {
    let cancelled = false;

    // Reset all chart data and states
    setAiLevelData([]);
    setSalaryDistData([]);
    setApprovalData([]);
    setDepartmentInsights([]);
    setIsRedisUnavailable(false);
    setErrorMessage(null);
    setIsLoading(true);

    const cycleParam = selectedCycleId || undefined;

    async function withRetry<T>(fn: () => Promise<T>, attempts = 3): Promise<T> {
      let lastError: unknown;
      for (let i = 0; i < attempts; i++) {
        try {
          return await fn();
        } catch (error) {
          lastError = error;
          // Don't retry 4xx/5xx HTTP errors with a proper response — those are deterministic.
          // Only retry network errors (no response), since dashboard endpoints sometimes
          // drop the connection transiently under concurrent load.
          if (axios.isAxiosError(error) && error.response) {
            throw error;
          }
          if (i < attempts - 1) {
            await new Promise((resolve) => setTimeout(resolve, 500 * (i + 1)));
          }
        }
      }
      throw lastError;
    }

    async function loadAllChartData() {
      let hasError = false;

      // Fetch all chart data in parallel, with auto-retry on transient network errors
      const results = await Promise.allSettled([
        withRetry(() => fetchAiLevelDistribution(cycleParam)),
        withRetry(() => fetchSalaryDistribution(cycleParam)),
        withRetry(() => fetchApprovalPipeline(cycleParam)),
        withRetry(() => fetchDashboardSnapshot(cycleParam)),
      ]);

      if (cancelled) return;

      // Process AI level distribution
      if (results[0].status === 'fulfilled') {
        setAiLevelData(results[0].value.items);
      } else {
        if (is503(results[0].reason)) {
          setIsRedisUnavailable(true);
        } else {
          hasError = true;
        }
      }

      // Process salary distribution
      if (results[1].status === 'fulfilled') {
        setSalaryDistData(results[1].value.items);
      } else {
        if (is503(results[1].reason)) {
          setIsRedisUnavailable(true);
        } else {
          hasError = true;
        }
      }

      // Process approval pipeline
      if (results[2].status === 'fulfilled') {
        setApprovalData(results[2].value.items);
      } else {
        if (is503(results[2].reason)) {
          setIsRedisUnavailable(true);
        } else {
          hasError = true;
        }
      }

      // Process department insights from snapshot
      if (results[3].status === 'fulfilled') {
        setDepartmentInsights(results[3].value.department_insights);
      } else {
        if (!is503(results[3].reason)) {
          hasError = true;
        }
      }

      if (hasError) {
        setErrorMessage('加载看板数据失败，请检查网络连接后刷新页面重试。');
      }

      setIsLoading(false);
    }

    void loadAllChartData();
    return () => { cancelled = true; };
  }, [selectedCycleId]);

  const isEmpty = !isLoading && !errorMessage && !isRedisUnavailable
    && !aiLevelData.length && !salaryDistData.length
    && !approvalData.length && !departmentInsights.length;

  return (
    <AppShell
      title="组织洞察看板"
      description="围绕评估周期查看 AI 等级分布、调薪幅度、审批进度与部门洞察，帮助管理者快速定位重点。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">
            返回工作台
          </Link>
          <Link className="action-primary" to="/approvals">
            打开审批中心
          </Link>
        </>
      }
    >
      {/* Cycle selector toolbar */}
      <section className="dashboard-toolbar surface-subtle animate-fade-up">
        <div>
          <p className="dashboard-toolbar-label">查看周期</p>
          <p className="dashboard-toolbar-note">切换周期后，看板会联动更新所有图表与部门数据。</p>
        </div>
        <div className="dashboard-toolbar-control">
          <select
            className="toolbar-input w-full"
            onChange={(event) => setSelectedCycleId(event.target.value)}
            value={selectedCycleId}
          >
            <option value="">全部可见周期</option>
            {cycles.map((cycle) => (
              <option key={cycle.id} value={cycle.id}>
                {cycle.name}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Error message */}
      {errorMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}

      {/* Redis unavailable warning */}
      {isRedisUnavailable ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-warning)' }}>
          缓存服务暂时不可用，数据加载可能较慢。请联系管理员检查 Redis 服务状态。
        </p>
      ) : null}

      {/* Loading indicator */}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载组织洞察看板...</p> : null}

      {/* Empty state */}
      {isEmpty ? (
        <div className="surface px-5 py-8 text-center">
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 4 }}>
            暂无看板数据
          </p>
          <p style={{ fontSize: 13, color: 'var(--color-steel)' }}>
            当前周期尚未产生评估或调薪记录。请先在工作台发起评估流程。
          </p>
        </div>
      ) : null}

      {/* KPI cards — self-polling, not dependent on chart data fetch */}
      {!isLoading ? <KpiCards cycleId={selectedCycleId || undefined} /> : null}

      {/* Two-column chart grid */}
      {!isLoading && !isEmpty ? (
        <>
          <div className="dashboard-charts-grid">
            <section className="surface animate-fade-up">
              <h3 className="section-title" style={{ padding: '16px 16px 0' }}>AI 等级分布</h3>
              <AILevelChart data={aiLevelData} isServiceUnavailable={isRedisUnavailable} />
            </section>
            <section className="surface animate-fade-up">
              <h3 className="section-title" style={{ padding: '16px 16px 0' }}>调薪幅度分布</h3>
              <SalaryDistChart data={salaryDistData} isServiceUnavailable={isRedisUnavailable} />
            </section>
          </div>

          {/* Full-width approval pipeline */}
          <section className="surface animate-fade-up">
            <h3 className="section-title" style={{ padding: '16px 16px 0' }}>审批流水线状态</h3>
            <ApprovalPipelineChart data={approvalData} isServiceUnavailable={isRedisUnavailable} />
          </section>

          {/* Full-width department insight table with drilldown */}
          <DepartmentInsightTable
            rows={departmentInsights}
            cycleId={selectedCycleId || undefined}
          />
        </>
      ) : null}

      <style>{`
        .dashboard-charts-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }
        @media (max-width: 899px) {
          .dashboard-charts-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </AppShell>
  );
}

function is503(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 503;
}
