interface PerformanceRecordsFiltersProps {
  year: string;
  setYear: (v: string) => void;
  department: string;
  setDepartment: (v: string) => void;
  availableYears: number[];
  departments: string[];
}

/**
 * Phase 34 UI-SPEC §8.1：绩效记录列表 filter row。
 * 仅含「年份 select + 部门 select」；搜索框暂不实现（D-14 暂不做）。
 */
export function PerformanceRecordsFilters({
  year,
  setYear,
  department,
  setDepartment,
  availableYears,
  departments,
}: PerformanceRecordsFiltersProps) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
      <select
        className="toolbar-input"
        style={{ minWidth: 120 }}
        value={year}
        onChange={(e) => setYear(e.target.value)}
        aria-label="按年份筛选"
      >
        <option value="">全部年份</option>
        {availableYears.map((y) => (
          <option key={y} value={String(y)}>
            {y} 年
          </option>
        ))}
      </select>
      <select
        className="toolbar-input"
        style={{ minWidth: 160 }}
        value={department}
        onChange={(e) => setDepartment(e.target.value)}
        aria-label="按部门筛选"
      >
        <option value="">全部部门</option>
        {departments.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
    </div>
  );
}
