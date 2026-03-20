export interface DimensionScoreDraft {
  code: string;
  label: string;
  score: number;
  rationale: string;
}

interface DimensionScoreEditorProps {
  dimensions: DimensionScoreDraft[];
  onChange: (dimensions: DimensionScoreDraft[]) => void;
}

export function DimensionScoreEditor({ dimensions, onChange }: DimensionScoreEditorProps) {
  function updateDimension(index: number, field: 'score' | 'rationale', value: number | string) {
    const next = dimensions.map((dimension, currentIndex) => {
      if (currentIndex !== index) {
        return dimension;
      }
      return {
        ...dimension,
        [field]: value,
      };
    });
    onChange(next);
  }

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Dimension Scores</p>
          <h3 className="mt-2 text-2xl font-bold text-ink">Review scoring by dimension</h3>
        </div>
        <span className="text-sm text-slate-500">{dimensions.length} dimensions</span>
      </div>
      <div className="mt-5 grid gap-4">
        {dimensions.map((dimension, index) => (
          <article key={dimension.code} className="rounded-[24px] border border-slate-200 p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{dimension.code}</p>
                <h4 className="mt-2 text-lg font-semibold text-ink">{dimension.label}</h4>
              </div>
              <label className="flex items-center gap-3 text-sm text-slate-600">
                <span>Score</span>
                <input
                  className="w-24 rounded-2xl border border-slate-200 px-3 py-2 text-right"
                  max={100}
                  min={0}
                  onChange={(event) => updateDimension(index, 'score', Number(event.target.value))}
                  type="number"
                  value={dimension.score}
                />
              </label>
            </div>
            <textarea
              className="mt-4 min-h-24 w-full rounded-[20px] border border-slate-200 px-4 py-3 text-sm leading-6 text-slate-700"
              onChange={(event) => updateDimension(index, 'rationale', event.target.value)}
              placeholder="Why was this score adjusted?"
              value={dimension.rationale}
            />
          </article>
        ))}
      </div>
    </section>
  );
}