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
    <section className="surface-subtle px-6 py-6">
      <div className="section-head">
        <div>
          <p className="eyebrow">维度分数</p>
          <h3 className="section-title">按维度复核评分</h3>
        </div>
        <span className="text-sm text-steel">{dimensions.length} 个维度</span>
      </div>
      <div className="mt-5 grid gap-4">
        {dimensions.map((dimension, index) => (
          <article key={dimension.code} className="list-row p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-steel">{dimension.code}</p>
                <h4 className="mt-2 text-lg font-semibold text-ink">{dimension.label}</h4>
              </div>
              <label className="flex items-center gap-3 text-sm text-steel">
                <span>分数</span>
                <input
                  className="toolbar-input h-10 w-24 px-3 text-right"
                  max={100}
                  min={0}
                  onChange={(event) => updateDimension(index, 'score', Number(event.target.value))}
                  type="number"
                  value={dimension.score}
                />
              </label>
            </div>
            <textarea
              className="toolbar-textarea mt-4 w-full"
              onChange={(event) => updateDimension(index, 'rationale', event.target.value)}
              placeholder="请填写该维度调整分数的原因。"
              value={dimension.rationale}
            />
          </article>
        ))}
      </div>
    </section>
  );
}
