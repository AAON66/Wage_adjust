import { useState } from 'react';

export interface EligibilityFilterValues {
  department?: string;
  status?: string;
  rule?: string;
  job_family?: string;
  job_level?: string;
}

interface EligibilityFiltersProps {
  onFilterChange: (filters: EligibilityFilterValues) => void;
  departments: string[];
  loading: boolean;
}

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '合格', value: 'eligible' },
  { label: '不合格', value: 'ineligible' },
  { label: '待定', value: 'pending' },
];

const RULE_OPTIONS = [
  { label: '全部', value: '' },
  { label: '入职时长', value: 'tenure' },
  { label: '调薪间隔', value: 'salary_interval' },
  { label: '绩效等级', value: 'performance' },
  { label: '假期天数', value: 'leave_days' },
];

export function EligibilityFilters({ onFilterChange, departments, loading }: EligibilityFiltersProps) {
  const [filters, setFilters] = useState<EligibilityFilterValues>({});

  function handleChange(key: keyof EligibilityFilterValues, value: string) {
    const next = { ...filters, [key]: value || undefined };
    setFilters(next);
    onFilterChange(next);
  }

  if (loading) {
    return (
      <div className="flex items-center gap-3 rounded-md border px-4 py-3" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}>
        <div className="h-4 w-24 animate-pulse rounded" style={{ background: 'var(--color-border)' }} />
        <div className="h-4 w-24 animate-pulse rounded" style={{ background: 'var(--color-border)' }} />
        <div className="h-4 w-24 animate-pulse rounded" style={{ background: 'var(--color-border)' }} />
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-sm text-steel">
        <span className="text-xs font-medium">部门</span>
        <select
          className="rounded border px-3 py-1.5 text-sm text-ink"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
          value={filters.department ?? ''}
          onChange={(e) => handleChange('department', e.target.value)}
        >
          <option value="">全部</option>
          {departments.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm text-steel">
        <span className="text-xs font-medium">资格状态</span>
        <select
          className="rounded border px-3 py-1.5 text-sm text-ink"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
          value={filters.status ?? ''}
          onChange={(e) => handleChange('status', e.target.value)}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm text-steel">
        <span className="text-xs font-medium">规则</span>
        <select
          className="rounded border px-3 py-1.5 text-sm text-ink"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
          value={filters.rule ?? ''}
          onChange={(e) => handleChange('rule', e.target.value)}
        >
          {RULE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm text-steel">
        <span className="text-xs font-medium">岗位族</span>
        <input
          className="rounded border px-3 py-1.5 text-sm text-ink"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
          placeholder="输入岗位族"
          value={filters.job_family ?? ''}
          onChange={(e) => handleChange('job_family', e.target.value)}
        />
      </label>

      <label className="flex flex-col gap-1 text-sm text-steel">
        <span className="text-xs font-medium">职级</span>
        <input
          className="rounded border px-3 py-1.5 text-sm text-ink"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
          placeholder="输入职级"
          value={filters.job_level ?? ''}
          onChange={(e) => handleChange('job_level', e.target.value)}
        />
      </label>
    </div>
  );
}
