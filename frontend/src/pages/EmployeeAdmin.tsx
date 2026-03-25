import axios from 'axios';
import { useEffect, useState } from 'react';

import { EmployeeArchiveManager } from '../components/employee/EmployeeArchiveManager';
import { AppShell } from '../components/layout/AppShell';
import { fetchEmployees } from '../services/employeeService';
import { fetchDepartments } from '../services/userAdminService';
import type { DepartmentRecord, EmployeeRecord } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { detail?: string; message?: string } | undefined;
    return payload?.detail ?? payload?.message ?? '员工档案管理操作失败。';
  }
  return '员工档案管理操作失败。';
}

export function EmployeeAdminPage() {
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadData() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [employeeResponse, departmentResponse] = await Promise.all([
        fetchEmployees({ page: 1, page_size: 100 }),
        fetchDepartments(),
      ]);
      setEmployees(employeeResponse.items);
      setDepartments(departmentResponse.items);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  return (
    <AppShell
      title="员工档案与手册"
      description="在这里维护员工档案，支持新增、修改和快速查看当前员工信息。"
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-success)' }}>{successMessage}</p> : null}
      {isLoading ? <p className="surface px-5 py-4 text-sm text-steel">正在加载员工档案数据...</p> : null}

      {!isLoading ? (
        <EmployeeArchiveManager
          departments={departments}
          employees={employees}
          onError={(message) => {
            setErrorMessage(message);
            setSuccessMessage(null);
          }}
          onReload={loadData}
          onSuccess={(message) => {
            setSuccessMessage(message);
            setErrorMessage(null);
          }}
          resolveError={resolveError}
        />
      ) : null}
    </AppShell>
  );
}
