interface HeatmapCell {
  department: string;
  level: string;
  intensity: number;
}

interface HeatmapChartProps {
  cells: HeatmapCell[];
}

function intensityClass(intensity: number): string {
  if (intensity >= 80) return 'bg-ink text-white';
  if (intensity >= 60) return 'bg-amber-200 text-ink';
  if (intensity >= 40) return 'bg-amber-100 text-amber-900';
  return 'bg-slate-100 text-slate-500';
}

export function HeatmapChart({ cells }: HeatmapChartProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div>
        <p className="text-sm uppercase tracking-[0.24em] text-ember">Heatmap</p>
        <h3 className="mt-2 text-2xl font-bold text-ink">Department capability density</h3>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cells.map((cell) => (
          <article key={`${cell.department}-${cell.level}`} className={`rounded-[22px] p-4 ${intensityClass(cell.intensity)}`}>
            <p className="text-xs uppercase tracking-[0.18em]">{cell.level}</p>
            <h4 className="mt-2 text-lg font-semibold">{cell.department}</h4>
            <p className="mt-2 text-sm">Intensity {cell.intensity}</p>
          </article>
        ))}
      </div>
    </section>
  );
}