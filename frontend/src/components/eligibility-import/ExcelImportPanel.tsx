import { useCallback, useRef, useState } from 'react';

import { useTaskPolling } from '../../hooks/useTaskPolling';
import {
  uploadEligibilityExcel,
  getTemplateUrl,
} from '../../services/eligibilityImportService';
import type { EligibilityImportType } from '../../services/eligibilityImportService';

interface ExcelImportPanelProps {
  importType: EligibilityImportType;
  label: string;
  onResult: (result: unknown) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ExcelImportPanel({ importType, label, onResult }: ExcelImportPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number; errors: number } | null>(null);

  const taskStatus = useTaskPolling(taskId, {
    onComplete: (result) => {
      setTaskId(null);
      onResult(result);
    },
    onError: (errMsg) => {
      setTaskId(null);
      setError(errMsg);
    },
    onProgress: setProgress,
  });

  const isPolling = taskId !== null && taskStatus !== null && (taskStatus.status === 'pending' || taskStatus.status === 'running');

  const handleFileSelect = useCallback((selected: File | null) => {
    if (!selected) return;
    const ext = selected.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx' && ext !== 'xls') {
      setError('仅支持 .xlsx 或 .xls 格式文件');
      return;
    }
    setFile(selected);
    setError(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFileSelect(dropped);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(null);
    try {
      const response = await uploadEligibilityExcel(importType, file);
      const data = response.data as { task_id: string };
      setTaskId(data.task_id);
    } catch {
      setError('文件上传失败，请重试');
    } finally {
      setUploading(false);
    }
  }, [file, importType]);

  const clearFile = useCallback(() => {
    setFile(null);
    setError(null);
    setProgress(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  return (
    <div>
      <p className="eyebrow">Excel 导入</p>
      <h3 className="section-title" style={{ marginBottom: 12 }}>
        上传{label}数据文件
      </h3>

      {/* File Drop Zone */}
      <div
        role="button"
        tabIndex={0}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        style={{
          border: `2px dashed ${dragOver ? 'var(--color-primary)' : 'var(--color-border)'}`,
          borderRadius: 8,
          padding: '32px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragOver ? 'var(--color-primary-light, rgba(59,130,246,0.05))' : 'transparent',
          transition: 'border-color 0.2s, background 0.2s',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          hidden
          onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, color: 'var(--color-ink)' }}>
              {file.name} ({formatFileSize(file.size)})
            </span>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); clearFile(); }}
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

      {error && (
        <p style={{ marginTop: 8, fontSize: 13, color: 'var(--color-danger)' }}>{error}</p>
      )}

      {/* Progress indicator */}
      {(uploading || isPolling) && (
        <p style={{ marginTop: 8, fontSize: 13, color: 'var(--color-primary)' }}>
          {uploading
            ? '正在上传文件...'
            : progress
              ? `正在导入数据... 已处理 ${progress.processed}/${progress.total} 条`
              : '正在导入数据...'}
        </p>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <a
          className="action-secondary"
          href={getTemplateUrl(importType)}
          target="_blank"
          rel="noopener noreferrer"
          style={{ textDecoration: 'none' }}
        >
          下载模板
        </a>
        <button
          className="action-primary"
          type="button"
          disabled={!file || uploading || isPolling}
          onClick={handleUpload}
        >
          开始导入
        </button>
      </div>
    </div>
  );
}
