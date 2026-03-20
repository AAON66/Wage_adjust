interface DistributionItem {
  label: string;
  value: number;
  colorClass: string;
}

interface DistributionChartProps {
  title: string;
  items: DistributionItem[];
}

export function DistributionChart({ title, items }: DistributionChartProps) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div>
        <p className="text-sm uppercase tracking-[0.24em] text-ember">Distribution</p>
        <h3 className="mt-2 text-2xl font-bold text-ink">{title}</h3>
      </div>
      <div className="mt-6 grid gap-4">
        {items.map((item) => {
          const width = total ? `${Math.round((item.value / total) * 100)}%` : '0%';
          return (
            <div key={item.label}>
              <div className="flex items-center justify-between gap-3 text-sm text-slate-600">
                <span>{item.label}</span>
                <span>{item.value}</span>
              </div>
              <div className="mt-2 h-3 rounded-full bg-slate-100">
                <div className={`h-3 rounded-full ${item.colorClass}`} style={{ width }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}