import axios from 'axios';
import { Link, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';

import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { fetchEmployees } from '../services/employeeService';
import type { EmployeeListResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? 'Failed to load employees.';
  }
  return 'Failed to load employees.';
}

export function EmployeesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<EmployeeListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const department = searchParams.get('department') ?? '';
  const jobFamily = searchParams.get('job_family') ?? '';
  const status = searchParams.get('status') ?? '';

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await fetchEmployees({
          page: 1,
          page_size: 20,
          department: department || undefined,
          job_family: jobFamily || undefined,
          status: status || undefined,
        });
        if (!cancelled) {
          setData(response);
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

    void load();
    return () => {
      cancelled = true;
    };
  }, [department, jobFamily, status]);

  function updateFilter(key: 'department' | 'job_family' | 'status', value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  return (
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[28px] bg-white p-6 shadow-panel">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-ember">Employees</p>
            <h1 className="mt-2 text-3xl font-bold">Employee Evaluation List</h1>
            <p className="mt-2 text-sm text-slate-500">This page reads directly from the backend `/api/v1/employees` API.</p>
          </div>
          <div className="flex gap-3">
            <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/workspace">
              Back to workspace
            </Link>
            <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/cycles/create">
              Create cycle
            </Link>
          </div>
        </header>

        <section className="grid gap-4 rounded-[28px] bg-white p-6 shadow-panel md:grid-cols-3">
          <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateFilter('department', event.target.value)} placeholder="Filter by department" value={department} />
          <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateFilter('job_family', event.target.value)} placeholder="Filter by job family" value={jobFamily} />
          <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateFilter('status', event.target.value)} placeholder="Filter by status" value={status} />
        </section>

        {isLoading ? <p className="text-sm text-slate-500">Loading employees...</p> : null}
        {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{errorMessage}</p> : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(data?.items ?? []).map((employee) => (
            <Link key={employee.id} className="rounded-[28px] bg-white p-6 shadow-panel transition hover:-translate-y-0.5 hover:shadow-xl" to={`/employees/${employee.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold">{employee.name}</h2>
                  <p className="mt-1 text-sm text-slate-500">{employee.employee_no}</p>
                </div>
                <StatusIndicator status={employee.status} />
              </div>
              <dl className="mt-4 space-y-2 text-sm text-slate-600">
                <div className="flex justify-between gap-4"><dt>Department</dt><dd>{employee.department}</dd></div>
                <div className="flex justify-between gap-4"><dt>Job family</dt><dd>{employee.job_family}</dd></div>
                <div className="flex justify-between gap-4"><dt>Job level</dt><dd>{employee.job_level}</dd></div>
              </dl>
              <div className="mt-5 flex items-center justify-between text-sm">
                <span className="text-slate-500">Open detail and evaluation status</span>
                <span className="font-semibold text-ember">Open</span>
              </div>
            </Link>
          ))}
        </section>

        {!isLoading && !errorMessage && data?.items.length === 0 ? (
          <section className="rounded-[28px] bg-white p-8 text-center shadow-panel">
            <h2 className="text-xl font-semibold">No employee records yet</h2>
            <p className="mt-2 text-sm text-slate-500">Create employees through the backend API and they will appear here.</p>
          </section>
        ) : null}
      </div>
    </main>
  );
}