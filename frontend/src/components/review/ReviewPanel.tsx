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

function weightedReviewScore(dimensions: DimensionScoreDraft[]): number {
  const totalWeight = dimensions.reduce((sum, dimension) => sum + dimension.weight, 0);
  if (!totalWeight) {
    return 0;
  }
  const weightedTotal = dimensions.reduce((sum, dimension) => sum + dimension.score * dimension.weight, 0);
  return Number((weightedTotal / totalWeight).toFixed(1));
}

function formatLevelLabel(level: string): string {
  return (
    {
      'Level 1': '一级',
      'Level 2': '二级',
      'Level 3': '三级',
      'Level 4': '四级',
      'Level 5': '五级',
    }[level] ?? level
  );
}

function formatStatusLabel(status: string): string {
  return (
    {
      draft: '未生成',
      generated: '已生成',
      pending_manager: '待主管复核',
      pending_hr: '待 HR 审核',
      returned: '已打回待补充',
      confirmed: '已确认',
    }[status] ?? status
  );
}

function statusColor(status: string): string {
  return ({
    draft: 'var(--color-steel)',
    generated: 'var(--color-info)',
    pending_manager: 'var(--color-warning)',
    pending_hr: 'var(--color-warning)',
    returned: 'var(--color-danger)',
    confirmed: 'var(--color-success)',
  } as Record<string, string>)[status] ?? 'var(--color-steel)';
}

function statusBg(status: string): string {
  return ({
    draft: 'var(--color-bg-subtle)',
    generated: 'var(--color-info-bg)',
    pending_manager: 'var(--color-warning-bg)',
    pending_hr: 'var(--color-warning-bg)',
    returned: 'var(--color-danger-bg)',
    confirmed: 'var(--color-success-bg)',
  } as Record<string, string>)[status] ?? 'var(--color-bg-subtle)';
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
  const reviewedScore = weightedReviewScore(dimensions);
  const isPendingHr = status === 'pending_hr';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, 1fr)' }} className="xl:grid-cols-4">
        {[
          { label: 'AI 初评分数', value: aiScore?.toFixed(1) ?? '--' },
          { label: '主管提交分数', value: managerScore?.toFixed(1) ?? '--' },
          { label: '评分差值', value: scoreGap != null ? (scoreGap > 0 ? `+${scoreGap.toFixed(1)}` : scoreGap.toFixed(1)) : '--' },
          { label: 'AI 建议等级', value: formatLevelLabel(aiLevel) },
        ].map((item) => (
          <div key={item.label} style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px' }}>
            <p style={{ fontSize: 11.5, color: 'var(--color-steel)', fontWeight: 500 }}>{item.label}</p>
            <p style={{ marginTop: 5, fontSize: 20, fontWeight: 600, color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>{item.value}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div style={{ background: statusBg(status), border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px' }}>
          <p style={{ fontSize: 11.5, color: 'var(--color-steel)', fontWeight: 500 }}>当前流程状态</p>
          <p style={{ marginTop: 5, fontSize: 14, fontWeight: 600, color: statusColor(status) }}>{formatStatusLabel(status)}</p>
        </div>
        <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px' }}>
          <p style={{ fontSize: 11.5, color: 'var(--color-steel)', fontWeight: 500 }}>当前复核总分</p>
          <p style={{ marginTop: 5, fontSize: 20, fontWeight: 600, color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>{reviewedScore}</p>
        </div>
        <label style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px', display: 'block' }}>
          <span style={{ fontSize: 11.5, color: 'var(--color-steel)', fontWeight: 500 }}>主管复核等级</span>
          <select
            className="toolbar-input"
            style={{ marginTop: 6, width: '100%' }}
            onChange={(e) => onReviewLevelChange(e.target.value)}
            value={reviewLevel}
          >
            {REVIEW_LEVEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      </div>

      <textarea
        className="toolbar-textarea"
        style={{ width: '100%' }}
        onChange={(e) => onReviewCommentChange(e.target.value)}
        placeholder="请用中文说明主管复核依据；如进入 HR 审核，请填写同意或打回的具体原因。"
        value={reviewComment}
      />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
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
    </div>
  );
}
