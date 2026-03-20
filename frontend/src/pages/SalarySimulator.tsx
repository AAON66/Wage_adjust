import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { BudgetSimulationPanel } from '../components/salary/BudgetSimulationPanel';
import { fetchCycles } from '../services/cycleService';
import { simulateSalary } from '../services/salaryService';
import type { CycleRecord, SalarySimulationResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      'Failed to load salary simulation.';
  }
  return 'Failed to load salary simulation.';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
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
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-start justify-between gap-4 rounded-[32px] bg-white p-6 shadow-panel">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Salary Simulator</p>
            <h1 className="mt-2 text-4xl font-bold">Compensation budget scenario board</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              This page now reads real cycle data and the live backend salary simulation API.
            </p>
          </div>
          <div className="flex gap-3">
            <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/workspace">
              Back to workspace
            </Link>
            <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/approvals">
              Open approvals
            </Link>
          </div>
        </header>

        <section className="rounded-[32px] bg-white p-6 shadow-panel">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="rounded-[24px] border border-slate-200 p-4">
              <span className="text-sm text-slate-500">Active cycle</span>
              <select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink" onChange={(event) => {
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
            <div className="rounded-[24px] border border-slate-200 p-4">
              <span className="text-sm text-slate-500">Current cycle context</span>
              <p className="mt-2 text-lg font-semibold text-ink">{selectedCycle?.review_period ?? 'No cycle selected'}</p>
              <p className="mt-2 text-sm text-slate-500">Status: {selectedCycle?.status ?? 'n/a'}</p>
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

        {isLoading ? <p className="text-sm text-slate-500">Loading simulation...</p> : null}
        {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{errorMessage}</p> : null}

        <section className="rounded-[32px] bg-white p-6 shadow-panel">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-ember">Simulation Rows</p>
              <h2 className="mt-2 text-3xl font-bold text-ink">Recommendation candidates</h2>
            </div>
            <span className="text-sm text-slate-500">{simulation?.items.length ?? 0} employees</span>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {(simulation?.items ?? []).map((item) => {
              const currentSalary = Number(item.current_salary);
              const projectedSalary = Number(item.recommended_salary);
              const increaseAmount = projectedSalary - currentSalary;
              return (
                <article key={item.employee_id} className="rounded-[24px] border border-slate-200 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-xl font-semibold text-ink">{item.employee_name}</h3>
                      <p className="mt-1 text-sm text-slate-500">{item.department} · {item.job_family}</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                      {(item.final_adjustment_ratio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <dl className="mt-4 space-y-2 text-sm text-slate-600">
                    <div className="flex justify-between gap-4"><dt>AI level</dt><dd>{item.ai_level}</dd></div>
                    <div className="flex justify-between gap-4"><dt>Current salary</dt><dd>{formatCurrency(currentSalary)}</dd></div>
                    <div className="flex justify-between gap-4"><dt>Suggested increase</dt><dd>{formatCurrency(increaseAmount)}</dd></div>
                    <div className="flex justify-between gap-4"><dt>Projected salary</dt><dd>{formatCurrency(projectedSalary)}</dd></div>
                  </dl>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
