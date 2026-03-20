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
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <article key={item.label} className="rounded-[28px] bg-white p-5 shadow-panel">
          <p className="text-sm text-slate-500">{item.label}</p>
          <p className="mt-3 text-3xl font-bold text-ink">{item.value}</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">{item.note}</p>
        </article>
      ))}
    </section>
  );
}