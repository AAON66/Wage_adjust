import type { SalaryRecommendationRecord, EvaluationRecord, SalaryHistoryRecord } from '../../types/api';
import type { SalaryFormatters } from './SalarySummaryPanel';
import { SalaryHistoryPanel } from './SalaryHistoryPanel';
import { DIMENSION_ORDER, DIMENSION_LABELS, DIMENSION_WEIGHTS } from '../../utils/dimensionConstants';

export interface SalaryDetailPanelProps {
  salaryRecommendation: SalaryRecommendationRecord;
  evaluation: EvaluationRecord | null;
  liveSalaryPreview: { recommendedRatio: number; finalAdjustmentRatio: number; recommendedSalary: number } | null;
  recommendationNeedsRefresh: boolean;
  isGeneratingSalary: boolean;
  canViewSalaryHistory: boolean;
  salaryHistory: SalaryHistoryRecord[];
  isSalaryHistoryLoading: boolean;
  selectedCycleId: string;
  employeeName: string | undefined;
  onGenerateSalary: () => void;
  fmt: SalaryFormatters;
}

export function SalaryDetailPanel({
  salaryRecommendation,
  evaluation,
  liveSalaryPreview,
  recommendationNeedsRefresh,
  isGeneratingSalary,
  canViewSalaryHistory,
  salaryHistory,
  isSalaryHistoryLoading,
  selectedCycleId,
  employeeName,
  onGenerateSalary,
  fmt,
}: SalaryDetailPanelProps) {
  return (
    <>
      {/* Dimension Score Table */}
      {evaluation?.dimension_scores?.length ? (
        <div className="table-shell">
          <table className="table-lite">
            <thead>
              <tr>
                <th>维度名</th>
                <th style={{ width: 80, textAlign: 'right' }}>得分</th>
                <th style={{ width: 80, textAlign: 'right' }}>权重</th>
                <th style={{ width: 80, textAlign: 'right' }}>加权分</th>
              </tr>
            </thead>
            <tbody>
              {DIMENSION_ORDER.map((code) => {
                const ds = evaluation.dimension_scores.find((d) => d.dimension_code === code);
                const weight = DIMENSION_WEIGHTS[code] ?? 0;
                const score = ds?.raw_score ?? 0;
                return (
                  <tr key={code}>
                    <td>{DIMENSION_LABELS[code] ?? code}</td>
                    <td style={{ textAlign: 'right' }}>{score.toFixed(1)}</td>
                    <td style={{ textAlign: 'right' }}>{(weight * 100).toFixed(0)}%</td>
                    <td style={{ textAlign: 'right' }}>{(score * weight).toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-steel">暂无维度评分数据</p>
      )}

      {/* Recommended ratio / AI multiplier / certification bonus */}
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">建议涨幅</p>
          <p className="mt-2 text-lg font-semibold text-ink">{fmt.formatPercent(salaryRecommendation.recommended_ratio, 2)}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">AI 系数</p>
          <p className="mt-2 text-lg font-semibold text-ink">{salaryRecommendation.ai_multiplier.toFixed(2)}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">认证加成</p>
          <p className="mt-2 text-lg font-semibold text-ink">{fmt.formatPercent(salaryRecommendation.certification_bonus, 2)}</p>
        </div>
      </div>

      {/* Recommended salary + status */}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">建议薪资</p>
          <p className="mt-2 text-lg font-semibold text-ink">{fmt.formatCurrency(salaryRecommendation.recommended_salary)}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">建议状态</p>
          <p className="mt-2 text-lg font-semibold text-ink">{fmt.formatRecommendationStatus(salaryRecommendation.status)}</p>
        </div>
      </div>

      {/* Live Preview Panel */}
      {liveSalaryPreview ? (
        <div className="mt-5">
          <div className="flex flex-wrap items-start justify-between gap-3 rounded-[8px] border px-4 py-4" style={{ borderColor: recommendationNeedsRefresh ? 'var(--color-warning)' : 'var(--color-border)', background: recommendationNeedsRefresh ? 'var(--color-warning-bg)' : 'var(--color-bg-subtle)' }}>
            <div>
              <p className="text-sm font-semibold text-ink">最新复核分联动预览</p>
              <p className="mt-2 text-sm leading-6 text-steel">这里显示的是按当前最终评分、等级和员工档案重新推算后的建议结果。</p>
            </div>
            <button
              className="action-secondary"
              disabled={isGeneratingSalary || !evaluation || evaluation.status !== 'confirmed'}
              onClick={onGenerateSalary}
              type="button"
            >
              {isGeneratingSalary ? '联动中...' : '按最新评分联动'}
            </button>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">最新复核分</p><p className="mt-2 text-lg font-semibold text-ink">{evaluation?.overall_score?.toFixed(1) ?? '--'}</p></div>
            <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">最新等级</p><p className="mt-2 text-lg font-semibold text-ink">{fmt.formatLevelLabel(evaluation?.ai_level ?? 'Level 1')}</p></div>
            <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后建议涨幅</p><p className="mt-2 text-lg font-semibold text-ink">{fmt.formatPercent(liveSalaryPreview.recommendedRatio, 2)}</p></div>
            <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后最终比例</p><p className="mt-2 text-lg font-semibold text-ink">{fmt.formatPercent(liveSalaryPreview.finalAdjustmentRatio, 2)}</p></div>
            <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后建议薪资</p><p className="mt-2 text-lg font-semibold text-ink">{fmt.formatCurrency(String(liveSalaryPreview.recommendedSalary.toFixed(2)))}</p></div>
          </div>
          {recommendationNeedsRefresh ? (
            <p className="mt-3 text-sm" style={{ color: 'var(--color-warning)' }}>
              当前页面展示的"建议涨幅 / AI 系数 / 认证加成 / 最终调整比例"还没有跟最新复核分同步，点击上面的"按最新评分联动"就会刷新。
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Explanation */}
      {salaryRecommendation.explanation ? (
        <details className="mt-5" style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '12px 16px' }}>
          <summary className="cursor-pointer text-sm font-semibold text-ink">查看建议说明</summary>
          <p className="mt-3 text-sm leading-7 text-steel">{salaryRecommendation.explanation}</p>
        </details>
      ) : null}

      {/* Salary History Panel */}
      {canViewSalaryHistory ? (
        <div className="mt-5">
          <SalaryHistoryPanel
            currentCycleId={selectedCycleId}
            employeeName={employeeName}
            history={salaryHistory}
            isLoading={isSalaryHistoryLoading}
          />
        </div>
      ) : null}
    </>
  );
}
