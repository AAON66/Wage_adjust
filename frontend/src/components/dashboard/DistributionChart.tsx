interface DistributionItem {
  label: string;
  value: number;
  colorClass: string;
}

interface DistributionChartProps {
  title: string;
  items: DistributionItem[];
}

const BAR_COLORS: Record<string, string> = {
  'bg-emerald-500': 'var(--color-success)',
  'bg-[#2d5cff]': 'var(--color-primary)',
  'bg-sky-400': '#38BDF8',
  'bg-sky-200': '#BAE6FD',
  'bg-slate-300': 'var(--color-border-strong)',
};

export function DistributionChart({ title, items }: DistributionChartProps) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">分布概览</p>
          <h3 className="section-title">{title}</h3>
        </div>
        <p className="text-sm text-steel">共 {total} 条记录</p>
      </div>
      <div className="mt-4 grid gap-2">
        {items.map((item) => {
          const ratio = total ? item.value / total : 0;
          const width = total ? `${Math.max(4, Math.round(ratio * 100))}%` : '0%';
          const barColor = BAR_COLORS[item.colorClass] ?? 'var(--color-primary)';
          return (
            <div className="surface-subtle px-4 py-3" key={item.label}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>{item.label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: 'var(--color-steel)', minWidth: 36, textAlign: 'right' }}>{Math.round(ratio * 100)}%</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)', minWidth: 24, textAlign: 'right' }}>{item.value}</span>
                </div>
              </div>
              <div style={{ height: 6, borderRadius: 3, background: 'var(--color-border)', overflow: 'hidden' }}>
                <div style={{ height: 6, borderRadius: 3, width, background: barColor, transition: 'width 0.4s ease' }} />
              </div>
            </div>
          );
        })}
        {!items.length ? (
          <p style={{ fontSize: 13, color: 'var(--color-steel)', padding: '12px 0' }}>暂无分布数据。</p>
        ) : null}
      </div>
    </section>
  );
}
