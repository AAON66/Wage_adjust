import { useEffect, useState } from 'react';

import { fetchEmployees } from '../../services/employeeService';
import type { ContributorInput, EmployeeRecord } from '../../types/api';

interface ContributorPickerProps {
  contributors: ContributorInput[];
  onChange: (contributors: ContributorInput[]) => void;
  disabled?: boolean;
}

export function ContributorPicker({ contributors, onChange, disabled = false }: ContributorPickerProps) {
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetchEmployees({ page: 1, page_size: 200 });
        if (!cancelled) {
          setEmployees(response.items);
        }
      } catch {
        // silently fail — picker will show empty dropdown
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
  }, []);

  const totalContributorPct = contributors.reduce((sum, c) => sum + c.contribution_pct, 0);
  const ownerPct = 100 - totalContributorPct;
  const isOverLimit = totalContributorPct > 99;

  function handleEmployeeChange(index: number, employeeId: string) {
    const next = contributors.map((c, i) => (i === index ? { ...c, employee_id: employeeId } : c));
    onChange(next);
  }

  function handlePctChange(index: number, value: string) {
    const pct = Math.max(0, Math.min(99, Number(value) || 0));
    const next = contributors.map((c, i) => (i === index ? { ...c, contribution_pct: pct } : c));
    onChange(next);
  }

  function handleAdd() {
    onChange([...contributors, { employee_id: '', contribution_pct: 0 }]);
  }

  function handleRemove(index: number) {
    onChange(contributors.filter((_, i) => i !== index));
  }

  if (isLoading) {
    return <p className="text-xs text-steel">加载员工列表...</p>;
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-ink">协作者分配</p>
        <button
          className="action-secondary px-3 py-1 text-xs"
          disabled={disabled}
          onClick={handleAdd}
          type="button"
        >
          + 添加协作者
        </button>
      </div>

      {contributors.map((contributor, index) => (
        <div key={index} className="flex items-center gap-2">
          <select
            className="toolbar-input flex-1"
            disabled={disabled}
            onChange={(e) => handleEmployeeChange(index, e.target.value)}
            value={contributor.employee_id}
          >
            <option value="">请选择员工</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.name} ({emp.employee_no})
              </option>
            ))}
          </select>
          <input
            className="toolbar-input w-20 text-center"
            disabled={disabled}
            max={99}
            min={1}
            onChange={(e) => handlePctChange(index, e.target.value)}
            placeholder="%"
            type="number"
            value={contributor.contribution_pct || ''}
          />
          <span className="text-xs text-steel">%</span>
          <button
            className="action-danger px-2 py-1 text-xs"
            disabled={disabled}
            onClick={() => handleRemove(index)}
            type="button"
          >
            移除
          </button>
        </div>
      ))}

      <div className={`text-xs ${isOverLimit ? 'text-[var(--color-danger)]' : 'text-steel'}`}>
        {isOverLimit
          ? `协作者百分比总和 ${totalContributorPct}% 超出限制，最多分配 99%`
          : `剩余比例（您的份额）: ${ownerPct}%`}
      </div>
    </div>
  );
}
