import { useEffect, useRef, useState } from 'react';

import { fetchEmployees } from '../../services/employeeService';
import type { ContributorInput, EmployeeRecord } from '../../types/api';

interface ContributorPickerProps {
  contributors: ContributorInput[];
  onChange: (contributors: ContributorInput[]) => void;
  disabled?: boolean;
}

function EmployeeSearchSelect({
  employees,
  value,
  disabled,
  onChange,
  alreadySelected,
}: {
  employees: EmployeeRecord[];
  value: string;
  disabled: boolean;
  onChange: (id: string) => void;
  alreadySelected: Set<string>;
}) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selected = employees.find((e) => e.id === value);

  const filtered = employees.filter((emp) => {
    if (alreadySelected.has(emp.id) && emp.id !== value) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      emp.name.toLowerCase().includes(q) ||
      emp.employee_no.toLowerCase().includes(q) ||
      (emp.department ?? '').toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={wrapperRef} style={{ position: 'relative', flex: 1 }}>
      <input
        className="toolbar-input w-full"
        disabled={disabled}
        placeholder={selected ? `${selected.name} (${selected.employee_no})` : '搜索员工姓名或工号...'}
        value={open ? query : selected ? `${selected.name} (${selected.employee_no})` : ''}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!open) setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          setQuery('');
        }}
      />
      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 50,
            maxHeight: 200,
            overflowY: 'auto',
            background: '#fff',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            marginTop: 4,
          }}
        >
          {filtered.length === 0 ? (
            <div style={{ padding: '8px 12px', fontSize: 13, color: 'var(--color-steel)' }}>
              未找到匹配员工
            </div>
          ) : (
            filtered.map((emp) => (
              <button
                key={emp.id}
                type="button"
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 12px',
                  fontSize: 13,
                  border: 'none',
                  background: emp.id === value ? 'var(--color-bg-subtle)' : 'transparent',
                  cursor: 'pointer',
                  color: 'var(--color-ink)',
                }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(emp.id);
                  setOpen(false);
                  setQuery('');
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLElement).style.background = 'var(--color-bg-subtle)';
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLElement).style.background = emp.id === value ? 'var(--color-bg-subtle)' : 'transparent';
                }}
              >
                <span style={{ fontWeight: 500 }}>{emp.name}</span>
                <span style={{ marginLeft: 6, color: 'var(--color-steel)' }}>
                  {emp.employee_no}
                </span>
                {emp.department ? (
                  <span style={{ marginLeft: 6, fontSize: 12, color: 'var(--color-steel)' }}>
                    · {emp.department}
                  </span>
                ) : null}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ContributorPicker({ contributors, onChange, disabled = false }: ContributorPickerProps) {
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetchEmployees({ page: 1, page_size: 100 });
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
  const alreadySelected = new Set(contributors.map((c) => c.employee_id).filter(Boolean));

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
          <EmployeeSearchSelect
            alreadySelected={alreadySelected}
            disabled={disabled}
            employees={employees}
            onChange={(id) => handleEmployeeChange(index, id)}
            value={contributor.employee_id}
          />
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
