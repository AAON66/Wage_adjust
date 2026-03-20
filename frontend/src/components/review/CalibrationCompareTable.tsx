interface CalibrationCompareRow {
  code: string;
  label: string;
  aiScore: number;
  manualScore: number;
  note: string;
}

interface CalibrationCompareTableProps {
  rows: CalibrationCompareRow[];
}

export function CalibrationCompareTable({ rows }: CalibrationCompareTableProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Calibration</p>
          <h3 className="mt-2 text-2xl font-bold text-ink">AI vs manual comparison</h3>
        </div>
        <span className="text-sm text-slate-500">{rows.length} rows</span>
      </div>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-3 text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-4">Dimension</th>
              <th className="px-4">AI</th>
              <th className="px-4">Manual</th>
              <th className="px-4">Delta</th>
              <th className="px-4">Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delta = row.manualScore - row.aiScore;
              const deltaClass = delta === 0 ? 'text-slate-500' : delta > 0 ? 'text-emerald-600' : 'text-rose-600';
              return (
                <tr key={row.code} className="rounded-[20px] bg-slate-50 text-slate-700">
                  <td className="rounded-l-[20px] px-4 py-4">
                    <div className="font-semibold text-ink">{row.label}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{row.code}</div>
                  </td>
                  <td className="px-4 py-4">{row.aiScore}</td>
                  <td className="px-4 py-4">{row.manualScore}</td>
                  <td className={`px-4 py-4 font-semibold ${deltaClass}`}>{delta > 0 ? `+${delta}` : `${delta}`}</td>
                  <td className="rounded-r-[20px] px-4 py-4">{row.note}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}