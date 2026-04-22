import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';

interface ReplaceModeConfirmModalProps {
  open: boolean;
  totalRows: number;
  onClose: () => void;
  onConfirm: () => void;
}

/**
 * D-11 + UI-SPEC §「Accessibility」+ T-32-15 mitigation
 *
 * 替换模式二次确认 Modal：
 * - 强制 checkbox 勾选「我已理解并确认」才能点「继续（替换模式）」
 * - role="dialog" + aria-modal="true" + aria-labelledby + aria-describedby
 * - focus trap：Tab/Shift+Tab 在 modal 内循环
 * - ESC 键关闭，焦点回到原触发按钮（由父组件持有焦点时机）
 * - 每次 open 重置 acknowledged state
 */
export function ReplaceModeConfirmModal({
  open,
  totalRows,
  onClose,
  onConfirm,
}: ReplaceModeConfirmModalProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const checkboxRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // 每次 open 重置 checkbox 并把焦点移入 modal 首个可交互元素（checkbox）
  useEffect(() => {
    if (open) {
      setAcknowledged(false);
      // setTimeout 0 让 DOM 渲染完成后再 focus
      const t = window.setTimeout(() => checkboxRef.current?.focus(), 0);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [open]);

  // ESC 关闭
  useEffect(() => {
    if (!open) return undefined;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // focus trap：Tab 在 modal 内循环
  const handleKeyDown = useCallback((e: ReactKeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'Tab') return;
    const focusables = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusables || focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="replace-modal-title"
        aria-describedby="replace-modal-body"
        className="surface animate-fade-up"
        style={{
          width: 'min(480px, 90vw)',
          maxHeight: '70vh',
          overflowY: 'auto',
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <h3 id="replace-modal-title" className="section-title">
          确认以替换模式导入 {totalRows} 行?
        </h3>
        <div
          id="replace-modal-body"
          style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--color-ink)' }}
        >
          <p style={{ margin: '0 0 12px 0' }}>
            <strong style={{ color: 'var(--color-danger)' }}>替换模式</strong> 会将 Excel 中为空的
            <strong>可选字段清空</strong>（设为 NULL），必填字段为空的行将失败。
          </p>
          <p style={{ margin: 0 }}>
            本操作会直接写入数据库，
            <strong style={{ color: 'var(--color-danger)' }}>已入库数据无法自动恢复</strong>
            ；请确认 Excel 中的空值均为你的预期。
          </p>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
          <input
            ref={checkboxRef}
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
          />
          我已理解并确认以替换模式导入，愿意承担空值清空的后果
        </label>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
          <button type="button" className="action-secondary" onClick={onClose}>
            返回
          </button>
          <button
            type="button"
            className="action-danger"
            disabled={!acknowledged}
            onClick={onConfirm}
            title={!acknowledged ? '请先勾选上方「我已理解并确认」复选框' : undefined}
          >
            继续（替换模式）
          </button>
        </div>
      </div>
    </div>
  );
}
