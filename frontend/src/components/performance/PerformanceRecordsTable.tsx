import type { CSSProperties } from 'react';

import type { PerformanceRecordItem } from '../../types/api';

interface PerformanceRecordsTableProps {
  items: PerformanceRecordItem[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}

/**
 * 等级 → status-pill 颜色映射（UI-SPEC §8.2）。
 * 全部使用 :root 既有 token，无未定义变量。
 */
const GRADE_STYLE: Record<string, CSSProperties> = {
  A: { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
  B: { background: 'var(--color-bg-subtle)', color: 'var(--color-ink)' },
  C: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  D: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  E: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
};

/**
 * B-5 修复：来源 chip 颜色映射，100% 使用 :root index.css 已定义的 token。
 * - manual → 灰底（--color-bg-subtle / --color-steel）
 * - excel → 蓝底（--color-primary-light / --color-primary）
 * - feishu → 紫底（--color-violet-bg / --color-violet，Phase 31 D-07 引入）
 */
const SOURCE_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  manual: {
    bg: 'var(--color-bg-subtle)',
    fg: 'var(--color-steel)',
    label: '手动',
  },
  excel: {
    bg: 'var(--color-primary-light)',
    fg: 'var(--color-primary)',
    label: '导入',
  },
  feishu: {
    bg: 'var(--color-violet-bg)',
    fg: 'var(--color-violet)',
    label: '飞书',
  },
};

function formatZhDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
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

function SourceCell({ source }: { source: string }) {
  const cfg = SOURCE_STYLE[source];
  if (!cfg) {
    return (
      <span
        className="status-pill"
        style={{ background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' }}
      >
        {source}
      </span>
    );
  }
  return (
    <span className="status-pill" style={{ background: cfg.bg, color: cfg.fg }}>
      {cfg.label}
    </span>
  );
}

/**
 * Phase 34 UI-SPEC §8.2 / §8.3：绩效记录表格 7 列 + 分页器。
 *
 * 列：员工工号 / 姓名 / 年份 / 绩效等级 / 部门快照 / 来源 / 录入时间
 *
 * - 工号：tabular-nums 等宽数字，保留前导零
 * - 部门快照：null → 「—」灰色 placeholder（D-07）
 * - 来源：B-5 三色映射只用真实存在的 :root token
 * - 不做行点击跳详情（N-3：Phase 36 范围）
 */
export function PerformanceRecordsTable({
  items,
  loading,
  total,
  page,
  pageSize: _pageSize,
  totalPages,
  onPageChange,
}: PerformanceRecordsTableProps) {
  void _pageSize; // pageSize 由父组件控制，此处仅展示
  return (
    <div className="table-shell">
      <table className="table-lite" style={{ width: '100%' }}>
        <caption className="sr-only">绩效记录列表（共 {total} 条）</caption>
        <thead>
          <tr>
            <th style={{ width: 120 }}>员工工号</th>
            <th style={{ width: 100 }}>姓名</th>
            <th style={{ width: 80 }}>年份</th>
            <th style={{ width: 80 }}>绩效等级</th>
            <th>部门快照</th>
            <th style={{ width: 100 }}>来源</th>
            <th style={{ width: 160 }}>录入时间</th>
          </tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: 5 }).map((_, idx) => (
              <tr key={`skeleton-${idx}`}>
                {Array.from({ length: 7 }).map((__, cellIdx) => (
                  <td key={cellIdx}>
                    <div
                      style={{
                        height: 12,
                        background: 'var(--color-bg-subtle)',
                        borderRadius: 4,
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          {!loading && items.length === 0 && (
            <tr>
              <td
                colSpan={7}
                style={{
                  textAlign: 'center',
                  padding: '32px 16px',
                  color: 'var(--color-placeholder)',
                }}
              >
                暂无数据
              </td>
            </tr>
          )}
          {!loading &&
            items.map((row) => (
              <tr key={row.id}>
                <td>
                  <span style={{ fontVariantNumeric: 'tabular-nums' }}>{row.employee_no}</span>
                </td>
                <td>{row.employee_name}</td>
                <td>{row.year} 年</td>
                <td>
                  <GradeCell grade={row.grade} />
                </td>
                <td>
                  {row.department_snapshot ?? (
                    <span style={{ color: 'var(--color-placeholder)' }}>—</span>
                  )}
                </td>
                <td>
                  <SourceCell source={row.source} />
                </td>
                <td>{formatZhDateTime(row.created_at)}</td>
              </tr>
            ))}
        </tbody>
      </table>
      {/* 分页器（UI-SPEC §8.3） */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderTop: '1px solid var(--color-border)',
          background: '#FFFFFF',
        }}
      >
        <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>
          共 {total} 条 · 第 {page}/{totalPages} 页
        </span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            type="button"
            className="chip-button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            上一页
          </button>
          <button
            type="button"
            className="chip-button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
}
