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

const REVIEW_LEVEL_OPTIONS = [
  { value: 'Level 1', label: '一级（Level 1）' },
  { value: 'Level 2', label: '二级（Level 2）' },
  { value: 'Level 3', label: '三级（Level 3）' },
  { value: 'Level 4', label: '四级（Level 4）' },
  { value: 'Level 5', label: '五级（Level 5）' },
];

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
    <section className="surface-subtle px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">人工复核</p>
          <h3 className="section-title">复核决策面板</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            对比 AI 输出与人工判断结果，完成复核意见提交或确认最终评估结论。
          </p>
        </div>
        <div className="surface-subtle px-4 py-3 text-right text-sm text-steel">
          <p>平均分</p>
          <p className="mt-1 text-xl font-semibold text-ink">{average}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">AI 推荐等级</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{aiLevel}</p>
        </div>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">人工复核等级</span>
          <select className="toolbar-input mt-3 w-full" onChange={(event) => onReviewLevelChange(event.target.value)} value={reviewLevel}>
            {REVIEW_LEVEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <textarea
        className="toolbar-textarea mt-5 w-full"
        onChange={(event) => onReviewCommentChange(event.target.value)}
        placeholder="记录复核意见、分歧原因和需要升级处理的上下文。"
        value={reviewComment}
      />

      <div className="mt-5 flex flex-wrap gap-3">
        <button className="action-primary" disabled={isSubmitting} onClick={onSubmitReview} type="button">
          {isSubmitting ? '提交中...' : '提交复核'}
        </button>
        <button className="action-secondary" disabled={isConfirming} onClick={onConfirmEvaluation} type="button">
          {isConfirming ? '确认中...' : '确认评估'}
        </button>
      </div>
    </section>
  );
}
