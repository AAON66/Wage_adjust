import { Link } from 'react-router-dom';
import type { SalaryRecommendationRecord, EvaluationRecord, EmployeeRecord } from '../../types/api';
import { EligibilityBadge } from '../eligibility/EligibilityBadge';

/** Formatting helpers passed from parent -- avoids duplicating logic */
export interface SalaryFormatters {
  formatRecommendationStatus: (status: string | null | undefined) => string;
  formatCurrency: (value: string) => string;
  formatPercent: (value: number | null | undefined, digits: number) => string;
  formatLevelLabel: (level: string) => string;
}

/** Manual adjustment editor state */
export interface ManualAdjustmentState {
  isSalaryEditorOpen: boolean;
  manualAdjustmentPercent: string;
  manualRecommendedSalary: string;
  isManualPercentValid: boolean;
  isManualSalaryValid: boolean;
  manualRecommendedSalaryNumber: number;
  manualSalaryDelta: number | null;
  baseSalaryAmount: number;
  canEdit: boolean;
  isSaving: boolean;
}

export interface SalarySummaryPanelProps {
  // Data
  salaryRecommendation: SalaryRecommendationRecord | null;
  evaluation: EvaluationRecord | null;
  employee: EmployeeRecord | null;
  userRole: string | undefined;

  // Grouped state
  manualAdjustment: ManualAdjustmentState;
  fmt: SalaryFormatters;

  // Scalar UI state
  isDetailExpanded: boolean;
  canSubmitApproval: boolean;
  isGeneratingSalary: boolean;
  isSubmittingApproval: boolean;

  // Handlers
  onToggleDetail: () => void;
  onGenerateSalary: () => void;
  onSubmitApproval: () => void;
  onSaveSalaryAdjustment: () => void;
  onCloseSalaryEditor: () => void;
  onManualPercentChange: (value: string) => void;
  onManualSalaryChange: (value: string) => void;
}

export function SalarySummaryPanel({
  salaryRecommendation,
  evaluation,
  employee,
  userRole,
  manualAdjustment,
  fmt,
  isDetailExpanded,
  canSubmitApproval,
  isGeneratingSalary,
  isSubmittingApproval,
  onToggleDetail,
  onGenerateSalary,
  onSubmitApproval,
  onSaveSalaryAdjustment,
  onCloseSalaryEditor,
  onManualPercentChange,
  onManualSalaryChange,
}: SalarySummaryPanelProps) {
  return (
    <>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 20 }}>
        <div>
          <p className="eyebrow">调薪建议</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">建议结果快照</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">查看建议薪资和审批动作。</p>
        </div>
        <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '10px 16px', textAlign: 'right' }}>
          <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>当前状态</p>
          <p className="mt-2 text-sm font-medium text-ink">{fmt.formatRecommendationStatus(salaryRecommendation?.status)}</p>
        </div>
      </div>

      {/* 3 Indicator Cards */}
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {/* Card 1: Eligibility Badge */}
        <EligibilityBadge
          employeeId={employee?.id ?? ''}
          userRole={userRole}
        />
        {/* Card 2: AI Score */}
        <div className="surface-subtle px-4 py-4">
          <p className="metric-label">AI 综合评分</p>
          <p className="metric-value mt-2">{evaluation?.overall_score?.toFixed(1) ?? '--'}</p>
          <p className="mt-1 text-sm text-steel">{fmt.formatLevelLabel(evaluation?.ai_level ?? '')}</p>
        </div>
        {/* Card 3: Current Salary */}
        <div className="surface-subtle px-4 py-4">
          <p className="metric-label">当前薪资</p>
          <p className="metric-value mt-2">{salaryRecommendation ? fmt.formatCurrency(salaryRecommendation.current_salary) : '--'}</p>
        </div>
      </div>

      {/* Featured Ratio */}
      <div className="mt-5 surface-subtle px-4 py-4">
        <p className="metric-label">最终调薪比例</p>
        <p className="metric-value mt-2" style={{ color: 'var(--color-primary)' }}>
          {fmt.formatPercent(salaryRecommendation?.final_adjustment_ratio, 2)}
        </p>
      </div>

      {salaryRecommendation ? (
        <>
          {/* Manual Adjustment Section */}
          <div className="mt-5" style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '18px 20px' }}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-ink">人工调整薪资窗口</p>
                <p className="mt-2 text-sm leading-6 text-steel">主管或 HR 可以在 AI 建议基础上手动调整最终涨幅和调整后薪资，再提交审批。</p>
              </div>
              <button
                className="action-secondary"
                disabled={!manualAdjustment.canEdit}
                onClick={onCloseSalaryEditor}
                type="button"
              >
                恢复当前建议
              </button>
            </div>

            {manualAdjustment.isSalaryEditorOpen ? (
              <div className="mt-5 grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm font-semibold text-ink">调整参数</p>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <label className="text-sm text-steel">
                      <span>人工调整比例（%）</span>
                      <input
                        className="toolbar-input mt-2 w-full"
                        max={100}
                        min={0}
                        onChange={(event) => onManualPercentChange(event.target.value)}
                        step="0.01"
                        type="number"
                        value={manualAdjustment.manualAdjustmentPercent}
                      />
                    </label>
                    <label className="text-sm text-steel">
                      <span>调整后薪资（元）</span>
                      <input
                        className="toolbar-input mt-2 w-full"
                        min={manualAdjustment.baseSalaryAmount}
                        onChange={(event) => onManualSalaryChange(event.target.value)}
                        step="0.01"
                        type="number"
                        value={manualAdjustment.manualRecommendedSalary}
                      />
                    </label>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="action-primary"
                      disabled={!manualAdjustment.isManualPercentValid || !manualAdjustment.isManualSalaryValid || manualAdjustment.isSaving}
                      onClick={onSaveSalaryAdjustment}
                      type="button"
                    >
                      {manualAdjustment.isSaving ? '保存中...' : '保存人工调整'}
                    </button>
                    <button className="action-secondary" disabled={manualAdjustment.isSaving} onClick={onCloseSalaryEditor} type="button">
                      取消
                    </button>
                  </div>

                  {!manualAdjustment.isManualPercentValid ? <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>调整比例需要填写 0 到 100 之间的数字。</p> : null}
                  {!manualAdjustment.isManualSalaryValid ? <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>调整后薪资不能低于当前薪资。</p> : null}
                </div>

                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm font-semibold text-ink">调整预览</p>
                  <div className="mt-4 space-y-3 text-sm text-steel">
                    <div className="flex items-center justify-between gap-4">
                      <span>AI 原建议薪资</span>
                      <span className="font-medium text-ink">{fmt.formatCurrency(salaryRecommendation.recommended_salary)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span>人工调整后薪资</span>
                      <span className="font-medium text-ink">{manualAdjustment.isManualSalaryValid ? fmt.formatCurrency(String(manualAdjustment.manualRecommendedSalaryNumber.toFixed(2))) : '--'}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span>人工调整比例</span>
                      <span className="font-medium text-ink">{manualAdjustment.isManualPercentValid ? `${manualAdjustment.manualAdjustmentPercent}%` : '--'}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span>预计调薪金额</span>
                      <span className="font-medium text-ink">{manualAdjustment.manualSalaryDelta != null ? fmt.formatCurrency(String(manualAdjustment.manualSalaryDelta.toFixed(2))) : '--'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {!manualAdjustment.canEdit ? (
              <p className="mt-4 text-sm" style={{ color: 'var(--color-warning)' }}>
                当前调薪建议已进入审批或锁定状态，暂时不能再做人工调整。
              </p>
            ) : null}
          </div>

          {/* Action Buttons */}
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              className="action-primary"
              disabled={
                !canSubmitApproval ||
                isSubmittingApproval ||
                salaryRecommendation.status === 'pending_approval' ||
                salaryRecommendation.status === 'approved' ||
                salaryRecommendation.status === 'locked'
              }
              onClick={onSubmitApproval}
              type="button"
            >
              {isSubmittingApproval ? '提交中...' : '提交审批'}
            </button>
            <Link className="chip-button" to="/approvals">
              查看审批中心
            </Link>
          </div>

          {!canSubmitApproval ? <p className="mt-3 text-sm" style={{ color: 'var(--color-warning)' }}>当前账号无法发起审批，请使用主管、HRBP 或管理员账号。</p> : null}

          {/* Expand/Collapse Toggle */}
          <button
            className="action-secondary mt-5"
            style={{ width: '100%' }}
            aria-expanded={isDetailExpanded}
            onClick={onToggleDetail}
            type="button"
          >
            {isDetailExpanded ? '收起' : '展开详情'}
          </button>
        </>
      ) : (
        /* Empty state */
        <div className="mt-5" style={{ border: '1px dashed var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px 20px', fontSize: 14, lineHeight: 1.8, color: 'var(--color-steel)' }}>
          <p className="font-semibold text-ink">还未生成调薪建议</p>
          <p>先确认评估结果，再生成调薪建议。</p>
          <button
            className="action-primary mt-3"
            disabled={isGeneratingSalary}
            onClick={onGenerateSalary}
            type="button"
          >
            {isGeneratingSalary ? '生成中...' : '生成调薪建议'}
          </button>
        </div>
      )}
    </>
  );
}
