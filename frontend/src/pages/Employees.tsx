import axios from 'axios';
import { Link, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { fetchEmployees } from '../services/employeeService';
import type { EmployeeListResponse } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? '加载员工列表失败。';
  }
  return '加载员工列表失败。';
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
    <AppShell
      title="员工评估列表"
      description="筛选员工并进入评估详情。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="action-primary" to="/cycles/create">创建周期</Link>
        </>
      }
    >
      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="grid gap-3 md:grid-cols-3">
          <input className="toolbar-input" onChange={(event) => updateFilter('department', event.target.value)} placeholder="按部门筛选" value={department} />
          <input className="toolbar-input" onChange={(event) => updateFilter('job_family', event.target.value)} placeholder="按岗位族筛选" value={jobFamily} />
          <input className="toolbar-input" onChange={(event) => updateFilter('status', event.target.value)} placeholder="按状态筛选" value={status} />
        </div>
      </section>

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载员工列表...</p> : null}
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(data?.items ?? []).map((employee, index) => (
          <Link className="list-row animate-fade-up" key={employee.id} style={{ animationDelay: `${index * 40}ms` }} to={`/employees/${employee.id}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-ink)' }}>{employee.name}</h2>
                <p className="mt-1 text-sm text-steel">{employee.employee_no}</p>
              </div>
              <StatusIndicator status={employee.status} />
            </div>
            <dl className="mt-5 space-y-3 text-sm text-steel">
              <div className="flex justify-between gap-4"><dt>部门</dt><dd className="text-ink">{employee.department}</dd></div>
              <div className="flex justify-between gap-4"><dt>岗位族</dt><dd className="text-ink">{employee.job_family}</dd></div>
              <div className="flex justify-between gap-4"><dt>岗位级别</dt><dd className="text-ink">{employee.job_level}</dd></div>
            </dl>
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--color-border)', fontSize: 13, color: 'var(--color-primary)' }}>进入详情并继续处理</div>
          </Link>
        ))}
      </section>

      {!isLoading && !errorMessage && data?.items.length === 0 ? (
        <section className="surface px-6 py-8 text-center">
          <h2 className="text-xl font-semibold text-ink">当前还没有员工记录</h2>
          <p className="mt-2 text-sm text-steel">创建员工数据后，这里会自动展示对应记录。</p>
        </section>
      ) : null}
    </AppShell>
  );
}
