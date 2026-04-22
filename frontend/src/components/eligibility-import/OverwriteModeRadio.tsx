import type { OverwriteMode } from '../../types/api';

interface OverwriteModeRadioProps {
  value: OverwriteMode;
  onChange: (value: OverwriteMode) => void;
  disabled?: boolean;
}

/**
 * D-11 + UI-SPEC §「Copywriting > 覆盖模式选择区」
 *
 * merge / replace 互斥 Radio：
 * - merge（默认推荐）：空值保留旧值，适合常规维护
 * - replace（破坏性）：空值清空字段；选中时显示 inline 警告（红底红字）
 *
 * 文案严格按 UI-SPEC 落地，不允许微调。
 */
export function OverwriteModeRadio({ value, onChange, disabled }: OverwriteModeRadioProps) {
  return (
    <fieldset
      style={{
        border: 'none',
        padding: 0,
        margin: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <legend className="section-title" style={{ marginBottom: 4 }}>
        覆盖模式
      </legend>

      <label
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          cursor: disabled ? 'not-allowed' : 'pointer',
        }}
      >
        <input
          type="radio"
          name="overwrite_mode"
          value="merge"
          checked={value === 'merge'}
          onChange={() => onChange('merge')}
          disabled={disabled}
          style={{ marginTop: 4 }}
        />
        <div>
          <div style={{ fontSize: 14, color: 'var(--color-ink)', fontWeight: 500 }}>
            合并模式（空值保留旧值，推荐）
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-steel)' }}>
            仅更新 Excel 中有值的字段；Excel 里为空的单元格不会改动已有数据。适合常规维护。
          </div>
        </div>
      </label>

      <label
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          cursor: disabled ? 'not-allowed' : 'pointer',
        }}
      >
        <input
          type="radio"
          name="overwrite_mode"
          value="replace"
          checked={value === 'replace'}
          onChange={() => onChange('replace')}
          disabled={disabled}
          style={{ marginTop: 4 }}
        />
        <div>
          <div style={{ fontSize: 14, color: 'var(--color-ink)', fontWeight: 500 }}>
            替换模式（空值清空字段）
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-steel)' }}>
            Excel 中为空的可选字段会被清空为 NULL；必填字段为空则该行失败。适合全量替换场景，
            <strong>操作不可自动回滚</strong>。
          </div>
        </div>
      </label>

      {value === 'replace' && (
        <div
          role="alert"
          className="animate-fade-soft"
          style={{
            background: 'var(--color-danger-bg)',
            borderLeft: '3px solid var(--color-danger)',
            color: 'var(--color-danger)',
            padding: '8px 12px',
            fontSize: 14,
            fontWeight: 500,
            borderRadius: 4,
          }}
        >
          ⚠ 替换模式会清空你未填的可选字段，这是破坏性操作。点击「确认导入」时需要再次确认。
        </div>
      )}
    </fieldset>
  );
}
