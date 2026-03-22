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
    <section className="surface" style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
        <div>
          <p className="eyebrow">评分协同</p>
          <h3 className="section-title">AI、主管与 HR 复核流程</h3>
          <p style={{ marginTop: 6, maxWidth: 560, fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>
            系统先依据材料生成 AI 初评，再由主管结合业务背景进行人工复核；当人工分与 AI 分差距较大时，会自动流转给 HR 做最终审核与确认。
          </p>
        </div>
        <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 16px', textAlign: 'right' }}>
          <p style={{ fontSize: 12, color: 'var(--color-steel)' }}>当前复核均分</p>
          <p style={{ marginTop: 4, fontSize: 22, fontWeight: 600, color: 'var(--color-ink)' }}>{average}</p>
        </div>
      </div>

      {/* Score tiles */}
      <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(2, 1fr)', marginBottom: 16 }} className="xl:grid-cols-4">
        {[
          { label: 'AI 初评得分', value: aiScore?.toFixed(1) ?? '--' },
          { label: '主管提交得分', value: managerScore?.toFixed(1) ?? '--' },
          { label: '评分差值', value: scoreGap?.toFixed(1) ?? '--' },
          { label: 'AI 建议等级', value: formatLevelLabel(aiLevel) },
        ].map((item) => (
          <div key={item.label} style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px' }}>
            <p style={{ fontSize: 12, color: 'var(--color-steel)' }}>{item.label}</p>
            <p style={{ marginTop: 6, fontSize: 20, fontWeight: 600, color: 'var(--color-ink)' }}>{item.value}</p>
          </div>
        ))}
      </div>

      {/* Status + level select */}
      <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(2, 1fr)', marginBottom: 16 }}>
        <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px' }}>
          <p style={{ fontSize: 12, color: 'var(--color-steel)' }}>当前流程状态</p>
          <p style={{ marginTop: 6, fontSize: 15, fontWeight: 600, color: 'var(--color-ink)' }}>{formatStatusLabel(status)}</p>
        </div>
        <label style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px', display: 'block' }}>
          <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>主管复核等级</span>
          <select
            className="toolbar-input"
            style={{ marginTop: 8, width: '100%' }}
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
        style={{ width: '100%', marginBottom: 16 }}
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
    </section>
  );
}
