import { useEffect } from 'react';

interface DuplicateWarningModalProps {
  isOpen: boolean;
  fileName: string;
  uploaderName: string;
  uploadedAt: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function formatUploadedAt(iso: string): string {
  if (!iso) return '';
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function DuplicateWarningModal({
  isOpen,
  fileName,
  uploaderName,
  uploadedAt,
  onConfirm,
  onCancel,
}: DuplicateWarningModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onConfirm, onCancel]);

  if (!isOpen) return null;

  const formattedAt = formatUploadedAt(uploadedAt);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        className="surface"
        style={{
          padding: '24px',
          borderRadius: 10,
          maxWidth: 420,
          width: '90%',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-warning)"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ flexShrink: 0 }}
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <h2
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: 'var(--color-ink)',
              lineHeight: 1.4,
              margin: 0,
            }}
          >
            文件内容重复
          </h2>
        </div>
        <p
          style={{
            fontSize: 13.5,
            color: 'var(--color-steel)',
            lineHeight: 1.6,
            margin: '0 0 12px 0',
          }}
        >
          此文件已由 <strong style={{ color: 'var(--color-ink)' }}>{uploaderName}</strong> 于{' '}
          <strong style={{ color: 'var(--color-ink)' }}>{formattedAt}</strong> 提交。继续上传将自动向对方发起共享申请。
        </p>
        <p
          style={{
            fontSize: 12,
            fontFamily: 'monospace',
            color: 'var(--color-ink)',
            wordBreak: 'break-all',
            margin: '0 0 20px 0',
            padding: '8px 10px',
            background: 'var(--color-bg-subtle)',
            borderRadius: 6,
          }}
        >
          {fileName}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            className="action-secondary"
            onClick={onCancel}
            type="button"
          >
            取消
          </button>
          <button
            className="action-primary"
            onClick={onConfirm}
            type="button"
          >
            继续上传
          </button>
        </div>
      </div>
    </div>
  );
}
