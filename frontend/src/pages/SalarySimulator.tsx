import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { BudgetSimulationPanel } from '../components/salary/BudgetSimulationPanel';
import { fetchCycles } from '../services/cycleService';
import { simulateSalary } from '../services/salaryService';
import type { CycleRecord, SalarySimulationResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载调薪模拟失败。';
  }
  return '加载调薪模拟失败。';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(value);
}

export function SalarySimulatorPage() {
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [budgetAmount, setBudgetAmount] = useState(0);
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [jobFamilyFilter, setJobFamilyFilter] = useState('');
  const [simulation, setSimulation] = useState<SalarySimulationResponse | null>(null);
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
        const firstCycle = response.items[0];
        if (firstCycle) {
          setSelectedCycleId(firstCycle.id);
          setBudgetAmount(Number(firstCycle.budget_amount));
        }
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
    async function loadSimulation() {
      if (!selectedCycleId) {
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await simulateSalary({
          cycle_id: selectedCycleId,
          budget_amount: budgetAmount ? String(budgetAmount) : undefined,
          department: departmentFilter || undefined,
          job_family: jobFamilyFilter || undefined,
        });
        if (!cancelled) {
          setSimulation(response);
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
    void loadSimulation();
    return () => {
      cancelled = true;
    };
  }, [selectedCycleId, budgetAmount, departmentFilter, jobFamilyFilter]);

  const selectedCycle = useMemo(() => cycles.find((cycle) => cycle.id === selectedCycleId) ?? null, [cycles, selectedCycleId]);
  const employees = useMemo(
    () =>
      (simulation?.items ?? []).map((item) => ({
        id: item.employee_id,
        name: item.employee_name,
        department: item.department,
        currentSalary: Number(item.current_salary),
        suggestedIncreaseRate: item.final_adjustment_ratio,
      })),
    [simulation],
  );
  const recommendedCost = useMemo(() => Number(simulation?.total_recommended_amount ?? 0), [simulation]);

  return (
    <AppShell
      title="调薪预算测算看板"
      description="查看预算范围内的调薪模拟结果。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="action-primary" to="/approvals">打开审批中心</Link>
        </>
      }
    >
      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">当前周期</span>
            <select className="toolbar-input mt-3 w-full" onChange={(event) => {
              const next = cycles.find((cycle) => cycle.id === event.target.value) ?? null;
              setSelectedCycleId(event.target.value);
              if (next) {
                setBudgetAmount(Number(next.budget_amount));
              }
            }} value={selectedCycleId}>
              {cycles.map((cycle) => (
                <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
              ))}
            </select>
          </label>
          <div className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">周期信息</span>
            <p className="mt-3 text-lg font-semibold text-ink">{selectedCycle?.review_period ?? '未选择周期'}</p>
            <p className="mt-2 text-sm text-steel">状态：{selectedCycle?.status ?? '无'}</p>
          </div>
        </div>
      </section>

      <BudgetSimulationPanel
        budgetAmount={budgetAmount}
        departmentFilter={departmentFilter}
        employees={employees}
        jobFamilyFilter={jobFamilyFilter}
        onBudgetAmountChange={setBudgetAmount}
        onDepartmentFilterChange={setDepartmentFilter}
        onJobFamilyFilterChange={setJobFamilyFilter}
        recommendedCost={recommendedCost}
      />

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载调薪模拟...</p> : null}
      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}

      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="section-head">
          <div>
            <p className="eyebrow">模拟结果</p>
            <h2 className="section-title">建议调薪名单</h2>
          </div>
          <span className="text-sm text-steel">{simulation?.items.length ?? 0} 名员工</span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {(simulation?.items ?? []).map((item) => {
            const currentSalary = Number(item.current_salary);
            const projectedSalary = Number(item.recommended_salary);
            const increaseAmount = projectedSalary - currentSalary;
            return (
              <article className="list-row" key={item.employee_id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)' }}>{item.employee_name}</h3>
                    <p className="mt-1 text-sm text-steel">{item.department} · {item.job_family}</p>
                  </div>
                  <span className="status-pill" style={{ background: 'var(--color-info-bg)', color: 'var(--color-info)' }}>
                    {(item.final_adjustment_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <dl className="mt-5 space-y-3 text-sm text-steel">
                  <div className="flex justify-between gap-4"><dt>AI 等级</dt><dd className="text-ink">{item.ai_level}</dd></div>
                  <div className="flex justify-between gap-4"><dt>当前薪资</dt><dd className="text-ink">{formatCurrency(currentSalary)}</dd></div>
                  <div className="flex justify-between gap-4"><dt>建议涨幅金额</dt><dd className="text-ink">{formatCurrency(increaseAmount)}</dd></div>
                  <div className="flex justify-between gap-4"><dt>调整后薪资</dt><dd className="text-ink">{formatCurrency(projectedSalary)}</dd></div>
                </dl>
              </article>
            );
          })}
        </div>
      </section>
    </AppShell>
  );
}
