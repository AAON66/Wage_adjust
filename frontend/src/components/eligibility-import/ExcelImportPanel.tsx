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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { status, progress, result, error: pollError, isPolling } = useTaskPolling(taskId);

  // When polling completes, relay result
  const prevStatusRef = useRef<string | null>(null);
  if (status !== prevStatusRef.current) {
    prevStatusRef.current = status;
    if (status === 'completed' && result) {
      onResult(result);
      setTaskId(null);
      setSelectedFile(null);
      setIsUploading(false);
    }
    if (status === 'failed') {
      setErrorMessage(pollError ?? '导入任务执行失败。');
      setTaskId(null);
      setIsUploading(false);
    }
  }

  const handleFileSelect = useCallback((file: File) => {
    const ext = file.name.toLowerCase();
    if (!ext.endsWith('.xlsx') && !ext.endsWith('.xls')) {
      setErrorMessage('仅支持 .xlsx 或 .xls 格式的 Excel 文件。');
      return;
    }
    setSelectedFile(file);
    setErrorMessage(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleClearFile = useCallback(() => {
    setSelectedFile(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleStartImport = useCallback(async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const response = await uploadEligibilityExcel(importType, selectedFile);
      setTaskId(response.task_id);
    } catch (err) {
      setIsUploading(false);
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('上传文件失败，请稍后重试。');
      }
    }
  }, [selectedFile, importType]);

  const dropZoneStyle: React.CSSProperties = {
    border: `2px dashed ${isDragOver ? 'var(--color-primary)' : 'var(--color-border)'}`,
    borderRadius: 8,
    padding: '32px 24px',
    textAlign: 'center',
    background: isDragOver ? 'var(--color-primary-light)' : 'var(--color-bg-subtle)',
    transition: 'border-color 0.12s, background 0.12s',
    cursor: 'pointer',
  };

  return (
    <section className="surface" style={{ padding: '16px 20px' }}>
      <p className="eyebrow">Excel 导入</p>
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        通过 Excel 文件导入{label}数据
      </h2>

      {!selectedFile ? (
        <div
          role="button"
          tabIndex={0}
          style={dropZoneStyle}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-steel)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ margin: '0 auto 8px' }}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p style={{ fontSize: 13.5, color: 'var(--color-steel)', margin: '0 0 4px' }}>
            拖拽 Excel 文件到此处，或点击选择文件
          </p>
          <p style={{ fontSize: 12, color: 'var(--color-placeholder)', margin: 0 }}>
            支持 .xlsx / .xls 格式，单次最多 5000 行
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '12px 16px',
            background: 'var(--color-bg-subtle)',
            borderRadius: 8,
            border: '1px solid var(--color-border)',
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-success)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: 13.5, color: 'var(--color-ink)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedFile.name}
            </p>
            <p style={{ fontSize: 12, color: 'var(--color-steel)', margin: 0 }}>
              {formatFileSize(selectedFile.size)}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClearFile}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              color: 'var(--color-steel)',
              lineHeight: 1,
            }}
            aria-label="清除已选文件"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        hidden
        onChange={handleInputChange}
      />

      {errorMessage ? (
        <p role="alert" style={{ marginTop: 8, fontSize: 13, color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}

      {(isUploading || isPolling) && progress ? (
        <p role="status" aria-live="polite" style={{ marginTop: 8, fontSize: 13, color: 'var(--color-steel)' }}>
          正在导入数据... 已处理 {progress.processed}/{progress.total} 条
        </p>
      ) : null}

      {(isUploading || isPolling) && !progress ? (
        <p role="status" aria-live="polite" style={{ marginTop: 8, fontSize: 13, color: 'var(--color-steel)' }}>
          正在导入数据...
        </p>
      ) : null}

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <a
          className="action-secondary"
          href={getTemplateUrl(importType)}
          download
          style={{ textDecoration: 'none' }}
        >
          下载模板
        </a>
        <button
          className="action-primary"
          type="button"
          disabled={!selectedFile || isUploading || isPolling}
          onClick={() => void handleStartImport()}
        >
          {isUploading || isPolling ? '导入中...' : '开始导入'}
        </button>
      </div>
    </section>
  );
}
