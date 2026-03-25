interface DistributionItem {
  label: string;
  value: number;
  colorClass: string;
}

interface DistributionChartProps {
  title: string;
  items: DistributionItem[];
  compact?: boolean;
}

const BAR_COLORS: Record<string, string> = {
  'bg-emerald-500': 'var(--color-success)',
  'bg-[#2d5cff]': 'var(--color-primary)',
  'bg-sky-400': '#38BDF8',
  'bg-sky-200': '#BAE6FD',
  'bg-slate-300': 'var(--color-border-strong)',
};

export function DistributionChart({ title, items, compact = false }: DistributionChartProps) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const sectionPadding = compact ? '20px 20px' : undefined;
  const itemPadding = compact ? '8px 12px' : '10px 14px';
  const itemGap = compact ? 6 : 8;
  const itemMarginBottom = compact ? 6 : 7;
  const labelFontSize = compact ? 12.5 : 13;
  const valueFontSize = compact ? 13 : 14;
  const barHeight = compact ? 4 : 5;

  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={sectionPadding ? { padding: sectionPadding } : undefined}>
      <div className="section-head">
        <div>
          <p className="eyebrow">分布概览</p>
          <h3 className="section-title">{title}</h3>
        </div>
        <p className="dashboard-summary-inline">共 {total} 条记录</p>
      </div>
      <div className="mt-4 grid gap-2">
        {items.map((item) => {
          const ratio = total ? item.value / total : 0;
          const width = total ? `${Math.max(4, Math.round(ratio * 100))}%` : '0%';
          const barColor = BAR_COLORS[item.colorClass] ?? 'var(--color-primary)';
          return (
            <div key={item.label} style={{ padding: itemPadding, borderRadius: 8, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: itemGap, marginBottom: itemMarginBottom }}>
                <span style={{ fontSize: labelFontSize, fontWeight: 500, color: 'var(--color-ink)' }}>{item.label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: compact ? 8 : 10 }}>
                  <span style={{ fontSize: 11, color: 'var(--color-steel)', minWidth: 32, textAlign: 'right' }}>{Math.round(ratio * 100)}%</span>
                  <span style={{ fontSize: valueFontSize, fontWeight: 700, color: 'var(--color-ink)', minWidth: 20, textAlign: 'right', letterSpacing: '-0.02em' }}>{item.value}</span>
                </div>
              </div>
              <div style={{ height: barHeight, borderRadius: 999, background: 'var(--color-border)', overflow: 'hidden' }}>
                <div style={{ height: barHeight, borderRadius: 999, width, background: barColor, transition: 'width 0.5s ease' }} />
              </div>
            </div>
          );
        })}
        {!items.length ? <p style={{ fontSize: 13, color: 'var(--color-steel)', padding: '12px 0' }}>暂无分布数据。</p> : null}
      </div>
    </section>
  );
}
