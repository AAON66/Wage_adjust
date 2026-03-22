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
        <article className="metric-tile" key={item.label} style={{ animationDelay: `${index * 60}ms` }}>
          <p className="metric-label">{item.label}</p>
          <p className="metric-value">{item.value}</p>
          <p className="metric-note">{item.note}</p>
        </article>
      ))}
    </section>
  );
}
