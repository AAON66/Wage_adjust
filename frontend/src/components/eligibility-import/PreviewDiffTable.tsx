import { useMemo, useState } from 'react';
import type { PreviewRow, PreviewRowAction } from '../../types/api';

interface PreviewDiffTableProps {
  rows: PreviewRow[];
  rowsTruncated?: boolean;
  truncatedCount?: number;
}

const ACTION_LABELS: Record<PreviewRowAction, string> = {
  insert: '新增',
  update: '更新',
  no_change: '无变化',
  conflict: '冲突',
};

const ACTION_INDICATOR_VAR: Record<PreviewRowAction, string> = {
  insert: '--color-success',
  update: '--color-info',
  no_change: '--color-steel',
  conflict: '--color-danger',
};

const PAGE_SIZE = 50;

/**
 * D-08 + D-10 + UI-SPEC §「Diff 表格行内着色」
 *
 * Preview Diff 表格：
 * - 50 行/页分页（D-10）
 * - no_change 默认折叠（chip-button 切换显示）
 * - conflict 行整行红底高亮 + 左侧 3px 红色指示条（D-08）
 * - 字段级 old → new 并排显示（FieldDiffsCell）
 */
export function PreviewDiffTable({ rows, rowsTruncated, truncatedCount }: PreviewDiffTableProps) {
  const [page, setPage] = useState(1);
  const [noChangeCollapsed, setNoChangeCollapsed] = useState(true);

  const visibleRows = useMemo(() => {
    return noChangeCollapsed ? rows.filter((r) => r.action !== 'no_change') : rows;
  }, [rows, noChangeCollapsed]);

  const noChangeCount = useMemo(
    () => rows.filter((r) => r.action === 'no_change').length,
    [rows],
  );

  const totalPages = Math.max(1, Math.ceil(visibleRows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pagedRows = visibleRows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {noChangeCount > 0 && (
        <button
          type="button"
          className="chip-button"
          onClick={() => {
            setNoChangeCollapsed((v) => !v);
            setPage(1);
          }}
          aria-expanded={!noChangeCollapsed}
          style={{ alignSelf: 'flex-start' }}
        >
          {noChangeCollapsed ? `显示未变化 ${noChangeCount} 行` : `收起未变化 ${noChangeCount} 行`}
        </button>
      )}

      <div className="table-shell">
        <table className="table-lite" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th scope="col" style={{ width: 64 }}>
                行号
              </th>
              <th scope="col" style={{ width: 120 }}>
                员工工号
              </th>
              <th scope="col" style={{ width: 80 }}>
                动作
              </th>
              <th scope="col">字段变更</th>
            </tr>
          </thead>
          <tbody>
            {pagedRows.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: 'var(--color-steel)', padding: 24 }}>
                  暂无可显示的变更行
                </td>
              </tr>
            )}
            {pagedRows.map((row) => {
              const isConflict = row.action === 'conflict';
              const isNoChange = row.action === 'no_change';
              const rowBg = isConflict
                ? 'var(--color-danger-bg)'
                : isNoChange
                  ? 'var(--color-bg-subtle)'
                  : 'transparent';
              const indicator = ACTION_INDICATOR_VAR[row.action];
              const conflictReasonId = isConflict
                ? `conflict-reason-${row.row_number}-${row.employee_no}`
                : undefined;
              return (
                <tr
                  key={`${row.row_number}-${row.employee_no}`}
                  style={{
                    background: rowBg,
                    borderLeft: `3px solid var(${indicator})`,
                  }}
                  aria-describedby={conflictReasonId}
                >
                  <td>{row.row_number}</td>
                  <td>{row.employee_no}</td>
                  <td>{ACTION_LABELS[row.action]}</td>
                  <td>
                    {isConflict ? (
                      <span id={conflictReasonId} style={{ color: 'var(--color-danger)' }}>
                        {row.conflict_reason ?? '冲突原因未提供'}
                      </span>
                    ) : isNoChange ? (
                      <span style={{ color: 'var(--color-steel)' }}>—</span>
                    ) : (
                      <FieldDiffsCell row={row} />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            className="chip-button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage === 1}
          >
            上一页
          </button>
          <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>
            第 {safePage} 页 共 {totalPages} 页 · 每页 {PAGE_SIZE} 行
          </span>
          <button
            type="button"
            className="chip-button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage === totalPages}
          >
            下一页
          </button>
        </div>
      )}

      {rowsTruncated && truncatedCount !== undefined && truncatedCount > 0 && (
        <p style={{ fontSize: 13, color: 'var(--color-steel)', margin: 0 }}>
          已省略 {truncatedCount} 行 no-change 展示
        </p>
      )}
    </div>
  );
}

function FieldDiffsCell({ row }: { row: PreviewRow }) {
  const entries = Object.entries(row.fields);
  if (entries.length === 0) {
    return <span style={{ color: 'var(--color-steel)' }}>—</span>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {entries.map(([fieldName, diff]) => {
        const oldDisplay = formatDiffValue(diff.old);
        const newDisplay = formatDiffValue(diff.new);
        return (
          <div key={fieldName} style={{ fontSize: 14 }}>
            <span style={{ color: 'var(--color-steel)', fontWeight: 600 }}>{fieldName}:</span>{' '}
            <span style={{ color: 'var(--color-steel)', textDecoration: 'line-through' }}>
              {oldDisplay}
            </span>
            <span style={{ color: 'var(--color-steel)', margin: '0 6px' }}>→</span>
            <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{newDisplay}</span>
          </div>
        );
      })}
    </div>
  );
}

function formatDiffValue(value: unknown | null): string {
  if (value === null || value === undefined || value === '') {
    return '(空)';
  }
  return String(value);
}
