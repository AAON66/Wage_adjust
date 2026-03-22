interface HeatmapCell {
  department: string;
  level: string;
  intensity: number;
}

interface HeatmapChartProps {
  cells: HeatmapCell[];
}

function intensityStyle(intensity: number): React.CSSProperties {
  if (intensity >= 80) return { background: 'var(--color-primary)', border: '1px solid var(--color-primary)', color: '#FFFFFF' };
  if (intensity >= 60) return { background: 'var(--color-primary-light)', border: '1px solid var(--color-primary-border)', color: 'var(--color-primary)' };
  if (intensity >= 40) return { background: '#EEF3FE', border: '1px solid var(--color-border)', color: 'var(--color-ink)' };
  return { background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', color: 'var(--color-steel)' };
}

function localizeLevel(level: string): string {
  return {
    'Level 1': '一级',
    'Level 2': '二级',
    'Level 3': '三级',
    'Level 4': '四级',
    'Level 5': '五级',
  }[level] ?? level;
}

import type React from 'react';

export function HeatmapChart({ cells }: HeatmapChartProps) {
  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">热度矩阵</p>
          <h3 className="section-title">部门能力密度</h3>
        </div>
        <p className="text-sm text-steel">按部门与优势等级聚合</p>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {cells.map((cell) => (
          <article
            key={`${cell.department}-${cell.level}`}
            style={{ borderRadius: 8, padding: '14px 16px', ...intensityStyle(cell.intensity) }}
          >
            <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.10em', opacity: 0.7 }}>{localizeLevel(cell.level)}</p>
            <h4 style={{ marginTop: 8, fontSize: 15, fontWeight: 600, lineHeight: 1.3 }}>{cell.department}</h4>
            <div style={{ marginTop: 12, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 8 }}>
              <p style={{ fontSize: 12, opacity: 0.8 }}>综合热度</p>
              <p style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1 }}>{cell.intensity}</p>
            </div>
          </article>
        ))}
        {!cells.length ? (
          <p style={{ fontSize: 13, color: 'var(--color-steel)', gridColumn: '1/-1' }}>暂无热度数据。</p>
        ) : null}
      </div>
    </section>
  );
}
