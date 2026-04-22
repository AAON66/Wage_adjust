import type { PreviewCounters } from '../../types/api';

interface PreviewCountersStripProps {
  counters: PreviewCounters;
}

interface CounterCellConfig {
  key: keyof PreviewCounters;
  label: string;
  mainTextVar: string;
  bgVar: string;
  borderVar: string;
  /** value > 0 时在数字下方显示的小字提示（仅 conflict 用） */
  subtitleWhenPositive?: string;
}

const CELLS: CounterCellConfig[] = [
  {
    key: 'insert',
    label: '新增',
    mainTextVar: '--color-success',
    bgVar: '--color-success-bg',
    borderVar: '--color-success-border',
  },
  {
    key: 'update',
    label: '更新',
    mainTextVar: '--color-info',
    bgVar: '--color-info-bg',
    borderVar: '--color-primary-border',
  },
  {
    key: 'no_change',
    label: '无变化',
    mainTextVar: '--color-steel',
    bgVar: '--color-bg-subtle',
    borderVar: '--color-border',
  },
  {
    key: 'conflict',
    label: '冲突',
    mainTextVar: '--color-danger',
    bgVar: '--color-danger-bg',
    borderVar: '--color-danger-border',
    subtitleWhenPositive: '需先修正',
  },
];

/**
 * D-08 + UI-SPEC §「Preview 4 色计数卡片专属色」
 *
 * 4 色计数卡片横条：insert（绿）/ update（蓝）/ no_change（steel）/ conflict（红）。
 * - 0 值弱化态：bg → bg-subtle，数值 → placeholder（与 Phase 31 CountersBadgeCluster 同源逻辑）
 * - conflict > 0 时显示「需先修正」副标题
 */
export function PreviewCountersStrip({ counters }: PreviewCountersStripProps) {
  return (
    <div
      role="group"
      aria-label="导入变更概览"
      style={{
        display: 'grid',
        gap: 16,
        gridTemplateColumns: 'repeat(4, 1fr)',
      }}
    >
      {CELLS.map((cell) => {
        const value = counters[cell.key];
        const zeroState = value === 0;
        const cellBg = zeroState ? 'var(--color-bg-subtle)' : `var(${cell.bgVar})`;
        const cellBorder = zeroState ? 'var(--color-border)' : `var(${cell.borderVar})`;
        const valueColor = zeroState ? 'var(--color-placeholder)' : `var(${cell.mainTextVar})`;
        const ariaLabel = zeroState
          ? `${cell.label} 类变更为 0 条`
          : `${cell.label} ${value} 条`;
        return (
          <div
            key={cell.key}
            role="status"
            aria-label={ariaLabel}
            style={{
              background: cellBg,
              border: `1px solid ${cellBorder}`,
              borderRadius: 8,
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <span className="eyebrow" style={{ color: 'var(--color-steel)' }}>
              {cell.label}
            </span>
            <span
              className="metric-value"
              style={{
                color: valueColor,
                fontSize: 26,
                fontWeight: 600,
                lineHeight: 1.1,
              }}
            >
              {value}
            </span>
            {!zeroState && cell.subtitleWhenPositive && (
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: `var(${cell.mainTextVar})`,
                }}
              >
                {cell.subtitleWhenPositive}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
