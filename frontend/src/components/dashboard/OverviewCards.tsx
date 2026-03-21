interface OverviewCardItem {
  label: string;
  value: string;
  note: string;
}

interface OverviewCardsProps {
  items: OverviewCardItem[];
}

export function OverviewCards({ items }: OverviewCardsProps) {
  return (
    <section className="metric-strip animate-fade-up">
      {items.map((item, index) => (
        <article className="metric-tile relative overflow-hidden" key={item.label} style={{ animationDelay: `${index * 80}ms` }}>
          <div className="absolute right-0 top-0 h-20 w-20 rounded-full bg-[#e6eeff] blur-2xl" />
          <div className="relative">
            <p className="metric-label">{item.label}</p>
            <p className="metric-value">{item.value}</p>
            <p className="metric-note">{item.note}</p>
          </div>
        </article>
      ))}
    </section>
  );
}
