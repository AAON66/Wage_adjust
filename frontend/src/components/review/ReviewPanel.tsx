import type { DimensionScoreDraft } from './DimensionScoreEditor';

interface ReviewPanelProps {
  aiLevel: string;
  reviewLevel: string;
  reviewComment: string;
  dimensions: DimensionScoreDraft[];
  isSubmitting?: boolean;
  isConfirming?: boolean;
  onReviewLevelChange: (value: string) => void;
  onReviewCommentChange: (value: string) => void;
  onSubmitReview: () => void;
  onConfirmEvaluation: () => void;
}

function averageScore(dimensions: DimensionScoreDraft[]): number {
  const total = dimensions.reduce((sum, dimension) => sum + dimension.score, 0);
  return dimensions.length ? Number((total / dimensions.length).toFixed(1)) : 0;
}

export function ReviewPanel({
  aiLevel,
  reviewLevel,
  reviewComment,
  dimensions,
  isSubmitting = false,
  isConfirming = false,
  onReviewLevelChange,
  onReviewCommentChange,
  onSubmitReview,
  onConfirmEvaluation,
}: ReviewPanelProps) {
  const average = averageScore(dimensions);

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Manual Review</p>
          <h3 className="mt-2 text-2xl font-bold text-ink">Reviewer decision panel</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Compare generated AI output against reviewer judgment, then submit or confirm the final evaluation.
          </p>
        </div>
        <div className="rounded-[24px] bg-slate-50 px-4 py-3 text-right text-sm text-slate-600">
          <p>Average score</p>
          <p className="mt-1 text-xl font-semibold text-ink">{average}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-[24px] border border-slate-200 p-4">
          <p className="text-sm text-slate-500">AI recommended level</p>
          <p className="mt-2 text-2xl font-bold text-ink">{aiLevel}</p>
        </div>
        <label className="rounded-[24px] border border-slate-200 p-4">
          <span className="text-sm text-slate-500">Manual review level</span>
          <select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink" onChange={(event) => onReviewLevelChange(event.target.value)} value={reviewLevel}>
            {['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5'].map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <textarea
        className="mt-5 min-h-32 w-full rounded-[24px] border border-slate-200 px-4 py-3 text-sm leading-6 text-slate-700"
        onChange={(event) => onReviewCommentChange(event.target.value)}
        placeholder="Capture reviewer notes, disagreements, and escalation context."
        value={reviewComment}
      />

      <div className="mt-5 flex flex-wrap gap-3">
        <button className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white disabled:opacity-60" disabled={isSubmitting} onClick={onSubmitReview} type="button">
          {isSubmitting ? 'Submitting...' : 'Submit review'}
        </button>
        <button className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink disabled:opacity-60" disabled={isConfirming} onClick={onConfirmEvaluation} type="button">
          {isConfirming ? 'Confirming...' : 'Confirm evaluation'}
        </button>
      </div>
    </section>
  );
}
