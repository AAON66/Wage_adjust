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
    <section className="table-shell animate-fade-up">
      <div className="section-head px-6 py-5">
        <div>
          <p className="eyebrow">校准对比</p>
          <h3 className="section-title">AI 与人工评分对照</h3>
        </div>
        <span className="text-sm text-steel">{rows.length} 条记录</span>
      </div>
      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>维度</th>
              <th>AI 评分</th>
              <th>人工评分</th>
              <th>差值</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delta = row.manualScore - row.aiScore;
              const deltaClass = delta === 0 ? 'text-steel' : delta > 0 ? 'text-emerald-600' : 'text-rose-600';
              return (
                <tr key={row.code}>
                  <td>
                    <div className="font-semibold text-ink">{row.label}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-steel">{row.code}</div>
                  </td>
                  <td>{row.aiScore}</td>
                  <td>{row.manualScore}</td>
                  <td className={`font-semibold ${deltaClass}`}>{delta > 0 ? `+${delta}` : `${delta}`}</td>
                  <td>{row.note}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
