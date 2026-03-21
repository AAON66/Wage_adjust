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
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">分布概览</p>
          <h3 className="section-title">{title}</h3>
        </div>
        <p className="text-sm text-steel">共 {total} 条记录</p>
      </div>
      <div className="mt-5 grid gap-3">
        {items.map((item) => {
          const ratio = total ? item.value / total : 0;
          const width = total ? `${Math.max(6, Math.round(ratio * 100))}%` : '0%';
          return (
            <div className="surface-subtle px-4 py-4 transition duration-200 hover:-translate-y-0.5 hover:border-[#c4d6ff]" key={item.label}>
              <div className="flex items-center justify-between gap-3 text-sm text-steel">
                <span>{item.label}</span>
                <span className="font-medium text-ink">{item.value}</span>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#e7eef9]">
                  <div className={`h-2.5 rounded-full ${item.colorClass}`} style={{ width }} />
                </div>
                <span className="min-w-[48px] text-right text-xs font-medium text-steel">{Math.round(ratio * 100)}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
