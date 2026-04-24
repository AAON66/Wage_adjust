import type { CSSProperties } from 'react';

import type { PerformanceRecordItem } from '../../types/api';

interface PerformanceHistoryPanelProps {
  employeeName?: string;
  records: PerformanceRecordItem[];
  isLoading: boolean;
}

const EM_DASH = '—';

const GRADE_STYLE: Record<string, CSSProperties> = {
  A: { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
  B: { background: 'var(--color-bg-subtle)', color: 'var(--color-ink)' },
  C: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  D: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  E: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
};

function formatCycleLabel(year: number): string {
  return `${year} 年度`;
}

function renderNullable(value: string | null | undefined): string {
  if (value == null) {
    return EM_DASH;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : EM_DASH;
}

function GradeCell({ grade }: { grade: string }) {
  const style = GRADE_STYLE[grade] ?? {
    background: 'var(--color-bg-subtle)',
    color: 'var(--color-ink)',
  };

  return (
    <span className="status-pill" style={style}>
      {grade}
    </span>
  );
}

export function PerformanceHistoryPanel({
  employeeName,
  records,
  isLoading,
}: PerformanceHistoryPanelProps) {
  if (isLoading) {
    return (
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">历史绩效</p>
            <h3 className="section-title">年度绩效记录</h3>
          </div>
        </div>
        <p className="mt-4 text-sm text-steel">正在加载该员工的历史绩效记录...</p>
      </section>
    );
  }

  if (!records.length) {
    return (
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">历史绩效</p>
            <h3 className="section-title">年度绩效记录</h3>
            <p className="section-note mt-2">
              {employeeName
                ? `${employeeName} 目前还没有可展示的历史绩效记录。`
                : '当前员工还没有可展示的历史绩效记录。'}
            </p>
          </div>
        </div>
        <div
          className="mt-5"
          style={{
            border: '1px dashed var(--color-border)',
            borderRadius: 8,
            background: 'var(--color-bg-subtle)',
            padding: '16px 20px',
          }}
        >
          <p className="text-sm font-semibold text-ink">暂无历史绩效记录</p>
          <p className="mt-2 text-sm leading-6 text-steel">该员工尚未录入任何年度绩效</p>
        </div>
      </section>
    );
  }

  return (
    <section className="surface px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">历史绩效</p>
          <h3 className="section-title">年度绩效记录</h3>
          <p className="section-note mt-2">
            {employeeName
              ? `${employeeName} 的跨年度绩效记录，按年度倒序展示。`
              : '按年度倒序查看该员工的历史绩效记录。'}
          </p>
        </div>
        <span
          className="status-pill"
          style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}
        >
          历史记录 {records.length} 条
        </span>
      </div>

      <div className="mt-5 table-shell">
        <table className="table-lite" style={{ width: '100%' }}>
          <caption className="sr-only">历史绩效记录列表</caption>
          <thead>
            <tr>
              <th style={{ width: 120 }}>周期</th>
              <th style={{ width: 120 }}>绩效等级</th>
              <th>评语</th>
              <th style={{ width: '28%' }}>部门快照</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {formatCycleLabel(record.year)}
                </td>
                <td>
                  <GradeCell grade={record.grade} />
                </td>
                <td
                  style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                  title={record.comment ?? undefined}
                >
                  {renderNullable(record.comment)}
                </td>
                <td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {renderNullable(record.department_snapshot)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
