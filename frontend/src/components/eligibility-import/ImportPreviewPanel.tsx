import { useState } from 'react';
import type { OverwriteMode, PreviewResponse } from '../../types/api';
import { OverwriteModeRadio } from './OverwriteModeRadio';
import { PreviewCountersStrip } from './PreviewCountersStrip';
import { PreviewDiffTable } from './PreviewDiffTable';
import { ReplaceModeConfirmModal } from './ReplaceModeConfirmModal';

interface ImportPreviewPanelProps {
  /** 资格类型中文标签（如「绩效档次」「调薪记录」「入司信息」「假期」），用于标题与文案 */
  label: string;
  preview: PreviewResponse;
  onConfirm: (overwriteMode: OverwriteMode) => Promise<void> | void;
  onCancel: () => void;
  /** confirm 进行中时禁用所有交互（避免双击重复请求） */
  isConfirming?: boolean;
}

/**
 * D-06 + UI-SPEC §「Component Inventory > 新增」
 *
 * Preview 面板整合壳：组合 4 个子组件 + ReplaceModeConfirmModal。
 * 受控状态：overwriteMode（默认 merge）+ modalOpen（仅 replace 模式弹出）。
 *
 * 主 CTA 行为：
 * - merge：直接调 onConfirm('merge')
 * - replace：先弹 ReplaceModeConfirmModal，勾选 checkbox 并点「继续」后调 onConfirm('replace')
 * - conflict > 0：禁用 + 提示「需先修正 Excel 后重新上传」
 *
 * Plan 06 在 ExcelImportPanel 中直接 `<ImportPreviewPanel ... />` 渲染即可，
 * 父组件只需处理 onConfirm（调 confirmImport service）+ onCancel（调 cancelImport service）。
 */
export function ImportPreviewPanel({
  label,
  preview,
  onConfirm,
  onCancel,
  isConfirming,
}: ImportPreviewPanelProps) {
  const [overwriteMode, setOverwriteMode] = useState<OverwriteMode>('merge');
  const [modalOpen, setModalOpen] = useState(false);

  const hasConflicts = preview.counters.conflict > 0;
  const conflictTooltip = hasConflicts
    ? `存在 ${preview.counters.conflict} 条冲突，请先修正 Excel 后重新上传`
    : undefined;

  const handlePrimaryClick = () => {
    if (hasConflicts || isConfirming) return;
    if (overwriteMode === 'replace') {
      setModalOpen(true);
      return;
    }
    void onConfirm('merge');
  };

  const handleModalConfirm = () => {
    setModalOpen(false);
    void onConfirm('replace');
  };

  const ctaLabel = overwriteMode === 'replace' ? '确认导入（替换模式）' : '确认导入';
  const expiresAt = new Date(preview.preview_expires_at).toLocaleString('zh-CN');

  return (
    <section
      aria-labelledby="preview-panel-title"
      className="surface animate-fade-up"
      style={{
        padding: '16px 20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}
    >
      <div>
        <p className="eyebrow">导入预览 · 确认前可检查</p>
        <h3 id="preview-panel-title" className="section-title">
          预览{label}导入结果（共 {preview.total_rows} 行）
        </h3>
        <p style={{ fontSize: 13, color: 'var(--color-steel)', margin: '4px 0 0' }}>
          已上传：{preview.file_name} · 本次预览将在 {expiresAt} 前有效
        </p>
        <p style={{ fontSize: 14, color: 'var(--color-ink)', margin: '8px 0 0' }}>
          下方展示本次导入会产生的变更。确认无误后点击「确认导入」才会写入数据库；
          若有冲突，请修正 Excel 后重新上传。
        </p>
      </div>

      <PreviewCountersStrip counters={preview.counters} />

      <PreviewDiffTable
        rows={preview.rows}
        rowsTruncated={preview.rows_truncated}
        truncatedCount={preview.truncated_count}
      />

      <OverwriteModeRadio value={overwriteMode} onChange={setOverwriteMode} disabled={isConfirming} />

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', position: 'relative' }}>
        <button
          type="button"
          className="action-secondary"
          onClick={onCancel}
          disabled={isConfirming}
        >
          取消本次预览
        </button>
        <button
          type="button"
          className="action-primary"
          disabled={hasConflicts || isConfirming}
          onClick={handlePrimaryClick}
          title={conflictTooltip}
          aria-describedby={hasConflicts ? 'conflict-disabled-reason' : undefined}
        >
          {ctaLabel}
        </button>
        {hasConflicts && (
          <span
            id="conflict-disabled-reason"
            style={{
              position: 'absolute',
              left: -9999,
              width: 1,
              height: 1,
              overflow: 'hidden',
            }}
          >
            {conflictTooltip}
          </span>
        )}
      </div>

      <ReplaceModeConfirmModal
        open={modalOpen}
        totalRows={preview.total_rows}
        onClose={() => setModalOpen(false)}
        onConfirm={handleModalConfirm}
      />
    </section>
  );
}
