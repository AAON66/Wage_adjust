import axios from 'axios';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { fetchEmployees } from '../services/employeeService';
import { fetchDepartments } from '../services/userAdminService';
import type { DepartmentRecord, EmployeeListResponse } from '../types/api';
import { canAccessDepartment, getScopedDepartmentNames, isDepartmentScopedRole } from '../utils/departmentScope';

const EMPLOYEE_STATUSES = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? '加载员工列表失败。';
  }
  return '加载员工列表失败。';
}

export function EmployeesPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<EmployeeListResponse | null>(null);
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [jobFamilies, setJobFamilies] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Keyword search state with IME composition guard
  const [keywordInput, setKeywordInput] = useState(searchParams.get('keyword') ?? '');
  const isComposingRef = useRef(false);
  const debounceTimerRef = useRef<number | null>(null);

  const department = searchParams.get('department') ?? '';
  const jobFamily = searchParams.get('job_family') ?? '';
  const status = searchParams.get('status') ?? '';
  const keyword = searchParams.get('keyword') ?? '';
  const isDepartmentScoped = isDepartmentScopedRole(user?.role);
  const scopedDepartments = useMemo(() => getScopedDepartmentNames(user), [user]);

  // Load departments and extract job families on mount
  useEffect(() => {
    let cancelled = false;

    async function loadFilterOptions() {
      try {
        const [deptResponse, empResponse] = await Promise.all([
          fetchDepartments(),
          fetchEmployees({ page: 1, page_size: 1000 }),
        ]);
        if (cancelled) return;

        setDepartments(deptResponse.items);

        // Extract distinct job families from employee data
        const families = new Set<string>();
        for (const emp of empResponse.items) {
          if (emp.job_family) {
            families.add(emp.job_family);
          }
        }
        setJobFamilies(Array.from(families).sort((a, b) => a.localeCompare(b, 'zh-CN')));
      } catch {
        // Silently fail — filters will just show no options
      }
    }

    void loadFilterOptions();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!isDepartmentScoped || canAccessDepartment(user, department)) {
      return;
    }
    const next = new URLSearchParams(searchParams);
    next.delete('department');
    setSearchParams(next, { replace: true });
  }, [department, isDepartmentScoped, searchParams, setSearchParams, user]);

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
          keyword: keyword || undefined,
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
  }, [department, jobFamily, status, keyword]);

  function updateFilter(key: 'department' | 'job_family' | 'status' | 'keyword', value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  const commitKeyword = useCallback(
    (value: string) => {
      updateFilter('keyword', value.trim());
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [searchParams, setSearchParams],
  );

  function handleKeywordChange(event: React.ChangeEvent<HTMLInputElement>) {
    const value = event.target.value;
    setKeywordInput(value);

    // Do not trigger search while IME is composing
    if (isComposingRef.current) return;

    // Debounce the search to avoid excessive API calls
    if (debounceTimerRef.current !== null) {
      window.clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = window.setTimeout(() => {
      commitKeyword(value);
      debounceTimerRef.current = null;
    }, 400);
  }

  function handleCompositionStart() {
    isComposingRef.current = true;
  }

  function handleCompositionEnd(event: React.CompositionEvent<HTMLInputElement>) {
    isComposingRef.current = false;
    const value = (event.target as HTMLInputElement).value;
    setKeywordInput(value);

    // Trigger search after composition ends
    if (debounceTimerRef.current !== null) {
      window.clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = window.setTimeout(() => {
      commitKeyword(value);
      debounceTimerRef.current = null;
    }, 400);
  }

  // Cleanup debounce timer on unmount
  useEffect(() => () => {
    if (debounceTimerRef.current !== null) {
      window.clearTimeout(debounceTimerRef.current);
    }
  }, []);

  // Determine department options based on role scope
  const departmentOptions = useMemo(() => {
    if (isDepartmentScoped) {
      return scopedDepartments.map((name) => ({ value: name, label: name }));
    }
    return departments
      .filter((d) => d.status === 'active')
      .map((d) => ({ value: d.name, label: d.name }));
  }, [isDepartmentScoped, scopedDepartments, departments]);

  return (
    <AppShell
      title="员工评估列表"
      description="筛选员工并进入评估详情。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">
            返回工作台
          </Link>
          <Link className="action-primary" to="/cycles/create">
            创建周期
          </Link>
        </>
      }
    >
      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {/* Department dropdown */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-steel">部门</span>
            <select
              className="toolbar-input"
              onChange={(event) => updateFilter('department', event.target.value)}
              value={department}
            >
              <option value="">{isDepartmentScoped ? '全部可见部门' : '全部部门'}</option>
              {departmentOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          {/* Job family dropdown */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-steel">岗位族</span>
            <select
              className="toolbar-input"
              onChange={(event) => updateFilter('job_family', event.target.value)}
              value={jobFamily}
            >
              <option value="">全部岗位族</option>
              {jobFamilies.map((family) => (
                <option key={family} value={family}>
                  {family}
                </option>
              ))}
            </select>
          </label>

          {/* Status dropdown */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-steel">状态</span>
            <select
              className="toolbar-input"
              onChange={(event) => updateFilter('status', event.target.value)}
              value={status}
            >
              <option value="">全部状态</option>
              {EMPLOYEE_STATUSES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          {/* Keyword search input with IME guard */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-steel">搜索</span>
            <input
              className="toolbar-input"
              onChange={handleKeywordChange}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              placeholder="按工号或姓名搜索"
              value={keywordInput}
            />
          </label>
        </div>
        {isDepartmentScoped ? (
          <p className="mt-3 text-sm text-steel">
            当前仅显示你已绑定的部门范围：{scopedDepartments.length ? scopedDepartments.join('、') : '暂无可见部门'}
          </p>
        ) : null}
      </section>

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载员工列表...</p> : null}
      {errorMessage ? (
        <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}

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
              <div className="flex justify-between gap-4">
                <dt>部门</dt>
                <dd className="text-ink">{employee.department}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>岗位族</dt>
                <dd className="text-ink">{employee.job_family}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>岗位级别</dt>
                <dd className="text-ink">{employee.job_level}</dd>
              </div>
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
