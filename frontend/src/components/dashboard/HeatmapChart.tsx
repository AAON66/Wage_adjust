interface HeatmapCell {
  department: string;
  level: string;
  intensity: number;
}

interface HeatmapChartProps {
  cells: HeatmapCell[];
}

function intensityClass(intensity: number): string {
  if (intensity >= 80) return 'border-[#2d5cff]/20 bg-[linear-gradient(180deg,#4179ff_0%,#2d5cff_100%)] text-white shadow-[0_18px_36px_rgba(51,112,255,0.22)]';
  if (intensity >= 60) return 'border-[#d5e2ff] bg-[linear-gradient(180deg,#eff4ff_0%,#dde8ff_100%)] text-[#1d3ea8]';
  if (intensity >= 40) return 'border-[#dde7f6] bg-[linear-gradient(180deg,#f6f9ff_0%,#edf3ff_100%)] text-[#365a99]';
  return 'border-[#e3ebf8] bg-[linear-gradient(180deg,#fbfdff_0%,#f6f9ff_100%)] text-steel';
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
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {cells.map((cell) => (
          <article className={`rounded-[24px] border px-5 py-5 transition duration-200 hover:-translate-y-0.5 ${intensityClass(cell.intensity)}`} key={`${cell.department}-${cell.level}`}>
            <p className="text-xs uppercase tracking-[0.18em] opacity-80">{localizeLevel(cell.level)}</p>
            <h4 className="mt-3 text-lg font-semibold">{cell.department}</h4>
            <div className="mt-4 flex items-end justify-between gap-3">
              <p className="text-sm opacity-90">综合热度</p>
              <p className="text-2xl font-semibold tracking-[-0.03em]">{cell.intensity}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
