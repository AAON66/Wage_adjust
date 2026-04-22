import { WarningIcon } from '../icons/NavIcons';
import type { ActualDistribution } from '../../types/api';

interface DistributionWarningBannerProps {
  actualDistribution: ActualDistribution;
}

interface RecomputeFailedBannerProps {
  /** ISO datetime 字符串（旧快照时间） */
  oldComputedAt: string;
  onRetry: () => void;
}

/** 把 0–1 小数转为 「N%」字符串（无小数位） */
function pct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

function formatZhDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Phase 34 UI-SPEC §6.2：档次分布偏离 20/70/10 警告横幅。
 * `role="alert"` 让 screen reader 即时读出。
 * `<WarningIcon style={{...}}/>` 使用 B-4 修复后的 IconProps.style 支持。
 */
export function DistributionWarningBanner({ actualDistribution }: DistributionWarningBannerProps) {
  return (
    <div
      role="alert"
      style={{
        padding: '12px 16px',
        borderRadius: 6,
        background: 'var(--color-warning-bg)',
        border: '1px solid var(--color-warning-border)',
        color: 'var(--color-warning)',
        fontSize: 13.5,
        lineHeight: 1.5,
        marginBottom: 16,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
      }}
    >
      <WarningIcon size={16} style={{ marginTop: 2, flexShrink: 0 }} />
      <span>
        档次分布偏离 20/70/10 超过 ±5%（实际{' '}
        <strong>
          {pct(actualDistribution['1'])}/{pct(actualDistribution['2'])}/{pct(actualDistribution['3'])}
        </strong>
        ）。建议复核绩效原始数据或调整评估口径。
      </span>
    </div>
  );
}

/**
 * Phase 34 D-04 / UI-SPEC §6.2 变体：重算失败时显示旧快照时间 + 立即重算 chip-button。
 */
export function RecomputeFailedBanner({ oldComputedAt, onRetry }: RecomputeFailedBannerProps) {
  return (
    <div
      role="alert"
      style={{
        padding: '12px 16px',
        borderRadius: 6,
        background: 'var(--color-warning-bg)',
        border: '1px solid var(--color-warning-border)',
        color: 'var(--color-warning)',
        fontSize: 13.5,
        lineHeight: 1.5,
        marginBottom: 16,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        flexWrap: 'wrap',
      }}
    >
      <WarningIcon size={16} style={{ marginTop: 2, flexShrink: 0 }} />
      <span style={{ flex: 1, minWidth: 0 }}>
        档次基于 {formatZhDateTime(oldComputedAt)} 的旧快照（重算失败，请重试）。
      </span>
      <button
        type="button"
        className="chip-button"
        onClick={onRetry}
        style={{ color: 'var(--color-warning)', borderColor: 'var(--color-warning-border)' }}
      >
        立即重算
      </button>
    </div>
  );
}
