import { useCallback, useEffect, useRef, useState } from 'react';

import {
  cancelImport,
  confirmImport,
  downloadTemplate,
  getActiveImportJob,
  uploadAndPreview,
} from '../../services/eligibilityImportService';
import type {
  ActiveJobResponse,
  ConfirmResponse,
  EligibilityImportType,
  OverwriteMode,
  PreviewResponse,
} from '../../types/api';
import { ImportActiveJobBanner } from './ImportActiveJobBanner';
import { ImportPreviewPanel } from './ImportPreviewPanel';

interface ExcelImportPanelProps {
  importType: EligibilityImportType;
  label: string;
  /**
   * 完成回调：confirm 成功后将 ConfirmResponse 透传给父组件。
   * Plan 06：父 ImportTabContent 不再渲染单独的 ImportResultPanel；
   * ExcelImportPanel 内部 'done' 分支已显示 success summary。
   */
  onComplete?: (result: ConfirmResponse) => void;
}

/**
 * Phase 32 D-06 / D-11 / D-18：ExcelImportPanel 7 态状态机。
 *
 * idle       — 默认态；可选择文件或下载模板
 * uploading  — 文件正在上传至 /excel/preview，显示进度
 * previewing — preview 已返回；渲染 ImportPreviewPanel 让 HR 检查 + 选 overwriteMode
 * confirming — 用户已点击「确认导入」，正在 POST /confirm
 * done       — confirm 成功；显示 inserted/updated/no_change/failed 计数 + 「继续导入新文件」
 * cancelled  — 用户取消 preview；展示提示后回到 idle
 * error      — 上传 / preview / confirm 失败；显示错误文案，不丢已上传文件
 */
type ImportFlowState =
  | { kind: 'idle' }
  | { kind: 'uploading'; file: File; progress: number }
  | { kind: 'previewing'; preview: PreviewResponse }
  | { kind: 'confirming'; preview: PreviewResponse; overwriteMode: OverwriteMode }
  | { kind: 'done'; result: ConfirmResponse }
  | { kind: 'cancelled' }
  | { kind: 'error'; message: string };

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface AxiosLikeError {
  response?: {
    status?: number;
    data?:
      | {
          detail?: { message?: string; error?: string } | string;
          error?: string;
          message?: string;
          import_type?: string;
        }
      | string;
  };
  message?: string;
}

function extractApiErrorMessage(err: unknown, fallback: string): { status?: number; message: string } {
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const ax = err as AxiosLikeError;
    const status = ax.response?.status;
    const data = ax.response?.data;
    if (data && typeof data === 'object') {
      // 顶层 {error, message, import_type}（main.py http_exception_handler dict detail）
      if ('message' in data && typeof data.message === 'string') {
        return { status, message: data.message };
      }
      // 兼容 {detail: {...}} 或 {detail: 'xxx'}
      const detail = data.detail;
      if (typeof detail === 'string') return { status, message: detail };
      if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
        return { status, message: detail.message };
      }
    } else if (typeof data === 'string') {
      return { status, message: data };
    }
    if (typeof ax.message === 'string') return { status, message: ax.message };
  }
  if (err instanceof Error) return { message: err.message };
  return { message: fallback };
}

export function ExcelImportPanel({ importType, label, onComplete }: ExcelImportPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [flow, setFlow] = useState<ImportFlowState>({ kind: 'idle' });
  const [activeJob, setActiveJob] = useState<ActiveJobResponse>({ active: false });
  const [activeJobLoading, setActiveJobLoading] = useState(true);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [pickedFile, setPickedFile] = useState<File | null>(null);

  // D-18: 进入 Tab 时查询是否有活跃 job；preview/confirm/cancel 后刷新
  const refreshActiveJob = useCallback(async () => {
    setActiveJobLoading(true);
    try {
      const resp = await getActiveImportJob(importType);
      setActiveJob(resp);
    } catch (err) {
      // 查询活跃 job 失败不阻断主流程，仅记录
      console.error('Failed to fetch active import job', err);
    } finally {
      setActiveJobLoading(false);
    }
  }, [importType]);

  useEffect(() => {
    void refreshActiveJob();
  }, [refreshActiveJob]);

  const isLocked = activeJob.active;
  const lockTooltip = isLocked
    ? `该类型导入正在进行中（${
        activeJob.status === 'previewing' ? '预览待确认' : '落库中'
      }）。请等待完成，或在「同步日志」查看进度。`
    : undefined;

  const handleFileSelect = useCallback((selected: File | null) => {
    if (!selected) return;
    const ext = selected.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx' && ext !== 'xls') {
      setFlow({ kind: 'error', message: '仅支持 .xlsx 或 .xls 格式文件' });
      return;
    }
    setPickedFile(selected);
    setFlow({ kind: 'idle' });
  }, []);

  const handleDownloadTemplate = useCallback(async () => {
    setDownloadingTemplate(true);
    try {
      await downloadTemplate(importType);
    } catch (err) {
      const { message } = extractApiErrorMessage(err, '模板下载失败');
      setFlow({
        kind: 'error',
        message: `模板下载失败：${message}。请刷新页面重试，或联系管理员确认后端服务状态。`,
      });
    } finally {
      setDownloadingTemplate(false);
    }
  }, [importType]);

  const handleUpload = useCallback(async () => {
    if (!pickedFile) return;
    setFlow({ kind: 'uploading', file: pickedFile, progress: 0 });
    try {
      const preview = await uploadAndPreview(importType, pickedFile, (percent) =>
        setFlow({ kind: 'uploading', file: pickedFile, progress: percent }),
      );
      setFlow({ kind: 'previewing', preview });
      await refreshActiveJob();
    } catch (err) {
      const { status, message } = extractApiErrorMessage(err, '文件上传失败');
      let displayMsg = message;
      if (status === 409) {
        displayMsg = message || '该类型导入正在进行中，请等待当前任务完成后再试。';
        await refreshActiveJob();
      } else if (status === 413) {
        displayMsg = '文件超过 10MB 上限，请缩减后重试。';
      } else if (status === 422) {
        displayMsg = `上传校验失败：${message || '文件类型不支持或字段缺失'}`;
      } else if (status === 401) {
        displayMsg = '会话已过期，请重新登录。';
      } else if (status === undefined) {
        // 网络错误或未达后端
        displayMsg = `网络错误：${message}`;
      }
      setFlow({ kind: 'error', message: displayMsg });
    }
  }, [pickedFile, importType, refreshActiveJob]);

  const handleConfirm = useCallback(
    async (overwriteMode: OverwriteMode) => {
      if (flow.kind !== 'previewing') return;
      const preview = flow.preview;
      setFlow({ kind: 'confirming', preview, overwriteMode });
      try {
        const result = await confirmImport(preview.job_id, overwriteMode, overwriteMode === 'replace');
        setFlow({ kind: 'done', result });
        onComplete?.(result);
        await refreshActiveJob();
      } catch (err) {
        const { status, message } = extractApiErrorMessage(err, '导入失败');
        let displayMsg = message;
        if (status === 422) {
          displayMsg = `替换模式确认未通过：${message}`;
        } else if (status === 409) {
          displayMsg = `当前任务状态冲突：${message}`;
        } else if (status === 404) {
          displayMsg = '本次预览的 job 已失效，请重新上传。';
        }
        setFlow({ kind: 'error', message: `导入失败：${displayMsg}` });
      }
    },
    [flow, onComplete, refreshActiveJob],
  );

  const handleCancel = useCallback(async () => {
    if (flow.kind !== 'previewing') return;
    const jobId = flow.preview.job_id;
    try {
      await cancelImport(jobId);
    } catch (err) {
      // cancel 失败不致命，记录后继续 reset
      console.error('Cancel import failed', err);
    }
    setFlow({ kind: 'cancelled' });
    setPickedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    await refreshActiveJob();
  }, [flow, refreshActiveJob]);

  const handleReset = useCallback(() => {
    setFlow({ kind: 'idle' });
    setPickedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const clearPickedFile = useCallback(() => {
    setPickedFile(null);
    setFlow({ kind: 'idle' });
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  // ===== 根据 flow.kind 渲染不同视图 =====

  // previewing / confirming：渲染 ImportPreviewPanel
  if (flow.kind === 'previewing' || flow.kind === 'confirming') {
    return (
      <ImportPreviewPanel
        label={label}
        preview={flow.preview}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isConfirming={flow.kind === 'confirming'}
      />
    );
  }

  // done：成功摘要 + 「继续导入新文件」
  if (flow.kind === 'done') {
    return (
      <div className="surface" style={{ padding: 24 }}>
        <p className="eyebrow">导入完成</p>
        <h3 className="section-title" style={{ color: 'var(--color-success)', marginBottom: 8 }}>
          导入成功
        </h3>
        <p style={{ fontSize: 14, color: 'var(--color-ink)', margin: '0 0 12px' }}>
          共处理 {flow.result.total_rows} 行：新增 {flow.result.inserted_count}、更新{' '}
          {flow.result.updated_count}、无变化 {flow.result.no_change_count}、失败{' '}
          {flow.result.failed_count}。
        </p>
        <p style={{ fontSize: 12, color: 'var(--color-steel)', margin: '0 0 16px' }}>
          耗时 {flow.result.execution_duration_ms} ms · 状态：{flow.result.status}
        </p>
        <button type="button" className="action-secondary" onClick={handleReset}>
          继续导入新文件
        </button>
      </div>
    );
  }

  // idle / uploading / cancelled / error：上传卡片
  const isUploading = flow.kind === 'uploading';

  return (
    <div>
      {activeJob.active && <ImportActiveJobBanner activeJob={activeJob} />}

      <p className="eyebrow">Excel 导入</p>
      <h3 className="section-title" style={{ marginBottom: 12 }}>
        上传{label}数据文件
      </h3>

      {/* File Drop Zone */}
      <div
        role="button"
        tabIndex={isLocked ? -1 : 0}
        aria-disabled={isLocked || undefined}
        onDrop={
          isLocked
            ? undefined
            : (e) => {
                e.preventDefault();
                setDragOver(false);
                const dropped = e.dataTransfer.files[0];
                if (dropped) handleFileSelect(dropped);
              }
        }
        onDragOver={
          isLocked
            ? undefined
            : (e) => {
                e.preventDefault();
                setDragOver(true);
              }
        }
        onDragLeave={() => setDragOver(false)}
        onClick={isLocked ? undefined : () => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (isLocked) return;
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        title={lockTooltip}
        style={{
          border: `2px dashed ${dragOver ? 'var(--color-primary)' : 'var(--color-border)'}`,
          borderRadius: 8,
          padding: '32px 24px',
          textAlign: 'center',
          cursor: isLocked ? 'not-allowed' : 'pointer',
          background: dragOver ? 'var(--color-primary-light, rgba(59,130,246,0.05))' : 'transparent',
          transition: 'border-color 0.2s, background 0.2s',
          opacity: isLocked ? 0.5 : 1,
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          hidden
          disabled={isLocked}
          onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
        />
        {pickedFile ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, color: 'var(--color-ink)' }}>
              {pickedFile.name} ({formatFileSize(pickedFile.size)})
            </span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                clearPickedFile();
              }}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-steel)',
                fontSize: 16,
                lineHeight: 1,
                padding: '2px 6px',
              }}
              aria-label="清除已选文件"
            >
              x
            </button>
          </div>
        ) : (
          <p style={{ fontSize: 14, color: 'var(--color-steel)', margin: 0 }}>
            将 .xlsx 或 .xls 文件拖拽到此处，或点击选择文件
          </p>
        )}
      </div>

      {flow.kind === 'error' && (
        <p
          role="alert"
          style={{ marginTop: 8, fontSize: 13, color: 'var(--color-danger)' }}
        >
          {flow.message}
        </p>
      )}

      {flow.kind === 'cancelled' && (
        <p
          role="status"
          style={{ marginTop: 8, fontSize: 13, color: 'var(--color-steel)' }}
        >
          已取消本次预览。可重新选择文件再次上传。
        </p>
      )}

      {isUploading && (
        <p
          aria-live="polite"
          style={{ marginTop: 8, fontSize: 13, color: 'var(--color-primary)' }}
        >
          正在上传文件...{flow.progress > 0 ? ` ${flow.progress}%` : ''}
        </p>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button
          type="button"
          className="action-secondary"
          onClick={handleDownloadTemplate}
          disabled={downloadingTemplate}
        >
          {downloadingTemplate ? '正在生成模板...' : '下载模板'}
        </button>
        <button
          type="button"
          className="action-primary"
          disabled={!pickedFile || isUploading || isLocked || activeJobLoading}
          onClick={handleUpload}
          title={isLocked ? lockTooltip : undefined}
        >
          上传并生成预览
        </button>
      </div>
    </div>
  );
}
