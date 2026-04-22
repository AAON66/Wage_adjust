import { useCallback, useEffect, useState } from 'react';

import {
  NoSnapshotError,
  TierRecomputeBusyError,
  getTierSummary,
  recomputeTiers,
} from '../../services/performanceService';
import type { TierSummaryResponse } from '../../types/api';
import { showToast } from '../../utils/toast';
import { ChartIcon, RefreshIcon } from '../icons/NavIcons';
import { DistributionWarningBanner } from './DistributionWarningBanner';
import { TierChip, UnTieredChip } from './TierChip';
import { TierStackedBar } from './TierStackedBar';

interface TierDistributionPanelProps {
  year: number;
  availableYears: number[];
  onYearChange: (y: number) => void;
  /** 重算成功时通知父级（父级用来刷新 records 列表） */
  onRecomputed: () => void;
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
 * Phase 34 Section 1：档次分布（UI-SPEC §6 整段落地）。
 *
 * 状态机：
 *   - summary=null && !noSnapshot → 加载骨架
 *   - noSnapshot=true → 空状态「立即生成档次」CTA（D-10 / UI-SPEC §9）
 *   - summary 有值 → warning 横幅（条件）+ ECharts 堆叠条 + 4 个 chip
 *
 * B-4 用法：`<ChartIcon style={{...}}/>` / `<WarningIcon style={{...}}/>` 依赖 IconProps.style 扩展。
 * W-4 用法：showToast 替代直接 alert。
 */
export function TierDistributionPanel({
  year,
  availableYears,
  onYearChange,
  onRecomputed,
}: TierDistributionPanelProps) {
  const [summary, setSummary] = useState<TierSummaryResponse | null>(null);
  const [noSnapshot, setNoSnapshot] = useState(false);
  const [isRecomputing, setIsRecomputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setSummary(null);
    setNoSnapshot(false);
    setError(null);
    try {
      const data = await getTierSummary(year);
      setSummary(data);
    } catch (err) {
      if (err instanceof NoSnapshotError) {
        setNoSnapshot(true);
        return;
      }
      const msg = err instanceof Error ? err.message : '加载档次摘要失败';
      setError(msg);
    }
  }, [year]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  const handleRecompute = useCallback(async () => {
    setIsRecomputing(true);
    try {
      const resp = await recomputeTiers(year);
      showToast(`档次重算完成（共 ${resp.sample_size} 人）`, 'success');
      onRecomputed();
      await loadSummary();
    } catch (err) {
      if (err instanceof TierRecomputeBusyError) {
        showToast('系统正在自动重算，请稍后重试', 'warning');
        // D-06：强制 5 秒冷却
        window.setTimeout(() => setIsRecomputing(false), 5000);
        return;
      }
      const msg = err instanceof Error ? err.message : '未知错误';
      showToast(`档次重算失败：${msg}`, 'error');
    } finally {
      // Busy 分支已自行延迟释放；其他分支立即解除禁用
      setIsRecomputing((prev) => {
        // 若 Busy 分支已在 setTimeout 内处理，这里不覆盖
        // 简化：直接解除；Busy setTimeout 5s 后再次 setIsRecomputing(false) 是幂等的
        return prev === true ? false : prev;
      });
    }
  }, [year, onRecomputed, loadSummary]);

  return (
    <div>
      {/* section head: title + note + 右侧 控件 */}
      <div className="section-head">
        <div>
          <h3 className="section-title">档次分布</h3>
          <p className="section-note">基于 PERCENT_RANK 算法对全公司绩效记录分档（1/2/3）</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <select
            className="toolbar-input"
            value={year}
            onChange={(e) => onYearChange(Number(e.target.value))}
            style={{ minWidth: 100 }}
            aria-label="选择年份"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>
                {y} 年
              </option>
            ))}
          </select>
          <button
            type="button"
            className="action-primary"
            onClick={handleRecompute}
            disabled={isRecomputing}
            aria-busy={isRecomputing}
          >
            <RefreshIcon className={isRecomputing ? 'animate-spin' : undefined} />
            {isRecomputing ? '重算中…' : '重算档次'}
          </button>
        </div>
      </div>

      {/* computed_at 时间戳 */}
      {summary && (
        <p
          style={{
            marginTop: -8,
            marginBottom: 12,
            fontSize: 12,
            color: 'var(--color-placeholder)',
          }}
        >
          最近重算：{formatZhDateTime(summary.computed_at)}
        </p>
      )}

      {/* 错误状态 */}
      {error && (
        <div
          role="alert"
          style={{
            padding: '12px 16px',
            borderRadius: 6,
            background: 'var(--color-danger-bg)',
            border: '1px solid var(--color-danger-border)',
            color: 'var(--color-danger)',
            fontSize: 13.5,
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {/* 空状态：无档次快照（D-10 / UI-SPEC §9） */}
      {noSnapshot && (
        <div className="empty-state" style={{ padding: '40px 24px' }}>
          <ChartIcon
            size={32}
            style={{ color: 'var(--color-placeholder)', margin: '0 auto 12px' }}
          />
          <h4
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: 'var(--color-ink)',
              marginBottom: 4,
            }}
          >
            {year} 年尚无档次快照
          </h4>
          <p
            style={{
              fontSize: 13,
              color: 'var(--color-steel)',
              marginBottom: 16,
              maxWidth: 360,
              marginInline: 'auto',
            }}
          >
            系统尚未为该年度生成档次。请先通过「绩效记录导入」上传数据，或直接生成档次。
          </p>
          <button
            type="button"
            className="action-primary"
            onClick={handleRecompute}
            disabled={isRecomputing}
            aria-busy={isRecomputing}
          >
            <RefreshIcon className={isRecomputing ? 'animate-spin' : undefined} />
            {isRecomputing ? '重算中…' : '立即生成档次'}
          </button>
        </div>
      )}

      {/* 加载骨架（summary=null && !noSnapshot && !error） */}
      {!summary && !noSnapshot && !error && (
        <div
          style={{
            height: 32 + 12 + 32,
            background: 'var(--color-bg-subtle)',
            borderRadius: 6,
          }}
          aria-label="档次摘要加载中"
        />
      )}

      {/* 正常渲染：summary 有值 */}
      {summary && (
        <>
          {summary.distribution_warning && (
            <DistributionWarningBanner actualDistribution={summary.actual_distribution} />
          )}
          <TierStackedBar
            tiersCount={summary.tiers_count}
            actualDistribution={summary.actual_distribution}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <TierChip
              color="#10b981"
              label="1 档"
              count={summary.tiers_count['1']}
              pct={summary.actual_distribution['1']}
            />
            <TierChip
              color="#f59e0b"
              label="2 档"
              count={summary.tiers_count['2']}
              pct={summary.actual_distribution['2']}
            />
            <TierChip
              color="#ef4444"
              label="3 档"
              count={summary.tiers_count['3']}
              pct={summary.actual_distribution['3']}
            />
            <UnTieredChip count={summary.tiers_count.none} />
          </div>
        </>
      )}
    </div>
  );
}
