import type { DimensionScoreDraft } from './DimensionScoreEditor';

interface ReviewPanelProps {
  status: string;
  aiLevel: string;
  aiScore: number | null;
  managerScore: number | null;
  scoreGap: number | null;
  reviewLevel: string;
  reviewComment: string;
  dimensions: DimensionScoreDraft[];
  canHrReview?: boolean;
  isSubmitting?: boolean;
  isConfirming?: boolean;
  isReturning?: boolean;
  onReviewLevelChange: (value: string) => void;
  onReviewCommentChange: (value: string) => void;
  onSubmitReview: () => void;
  onConfirmEvaluation: () => void;
  onReturnEvaluation?: () => void;
}

function averageScore(dimensions: DimensionScoreDraft[]): number {
  const total = dimensions.reduce((sum, dimension) => sum + dimension.score, 0);
  return dimensions.length ? Number((total / dimensions.length).toFixed(1)) : 0;
}

function formatLevelLabel(level: string): string {
  return {
    'Level 1': '一级',
    'Level 2': '二级',
    'Level 3': '三级',
    'Level 4': '四级',
    'Level 5': '五级',
  }[level] ?? level;
}

function formatStatusLabel(status: string): string {
  return {
    draft: '未生成',
    generated: '已生成',
    pending_manager: '待主管复核',
    pending_hr: '待 HR 审核',
    returned: '已打回待补充',
    confirmed: '已确认',
  }[status] ?? status;
}

const REVIEW_LEVEL_OPTIONS = [
  { value: 'Level 1', label: '一级' },
  { value: 'Level 2', label: '二级' },
  { value: 'Level 3', label: '三级' },
  { value: 'Level 4', label: '四级' },
  { value: 'Level 5', label: '五级' },
];

export function ReviewPanel({
  status,
  aiLevel,
  aiScore,
  managerScore,
  scoreGap,
  reviewLevel,
  reviewComment,
  dimensions,
  canHrReview = false,
  isSubmitting = false,
  isConfirming = false,
  isReturning = false,
  onReviewLevelChange,
  onReviewCommentChange,
  onSubmitReview,
  onConfirmEvaluation,
  onReturnEvaluation,
}: ReviewPanelProps) {
  const average = averageScore(dimensions);
  const isPendingHr = status === 'pending_hr';

  return (
    <section className="surface-subtle px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">评分协同</p>
          <h3 className="section-title">AI、主管与 HR 复核流程</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            系统先依据材料生成 AI 初评，再由主管结合业务背景进行人工复核；当人工分与 AI 分差距较大时，会自动流转给 HR 做最终审核与确认。
          </p>
        </div>
        <div className="surface-subtle px-4 py-3 text-right text-sm text-steel">
          <p>当前复核均分</p>
          <p className="mt-1 text-xl font-semibold text-ink">{average}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">AI 初评得分</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{aiScore?.toFixed(1) ?? '--'}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">主管提交得分</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{managerScore?.toFixed(1) ?? '--'}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">评分差值</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{scoreGap?.toFixed(1) ?? '--'}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">AI 建议等级</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatLevelLabel(aiLevel)}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">当前流程状态</p>
          <p className="mt-2 text-lg font-semibold text-ink">{formatStatusLabel(status)}</p>
        </div>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">主管复核等级</span>
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
        placeholder="请用中文说明主管复核依据；如进入 HR 审核，请填写同意或打回的具体原因。"
        value={reviewComment}
      />

      <div className="mt-5 flex flex-wrap gap-3">
        <button className="action-primary" disabled={isSubmitting || isPendingHr} onClick={onSubmitReview} type="button">
          {isSubmitting ? '提交中...' : '提交主管评分'}
        </button>
        {canHrReview && isPendingHr ? (
          <>
            <button className="action-secondary" disabled={isConfirming} onClick={onConfirmEvaluation} type="button">
              {isConfirming ? '处理中...' : 'HR 同意'}
            </button>
            <button className="action-danger" disabled={isReturning} onClick={onReturnEvaluation} type="button">
              {isReturning ? '处理中...' : 'HR 打回'}
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}