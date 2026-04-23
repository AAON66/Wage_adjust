import axios from 'axios';
import { Link } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';

import { fetchMyTier } from '../../services/performanceService';
import type { MyTierResponse } from '../../types/api';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'success'; data: MyTierResponse }
  | { kind: 'unbound' }
  | { kind: 'employee_missing' }
  | { kind: 'error'; message: string };

type TierVisualConfig = {
  bg: string;
  color: string;
  label: string;
  description: string | null;
};

/**
 * Phase 35 ESELF-03: 员工自助绩效档次徽章
 *
 * 严格约束：
 * - 不显示具体排名 / 百分位 / 同档其他人名单
 * - 不显示「优秀 / 合格 / 待提升」等语义标签，只显示 1/2/3 档
 * - 永远请求无参数路由 GET /performance/me/tier，避免横向越权
 */
export function MyPerformanceTierBadge() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  const load = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const data = await fetchMyTier();
      setState({ kind: 'success', data });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        if (status === 422) {
          setState({ kind: 'unbound' });
          return;
        }
        if (status === 404) {
          setState({ kind: 'employee_missing' });
          return;
        }
      }
      setState({ kind: 'error', message: '档次信息暂时不可用，请稍后重试' });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section
      className="surface px-6 py-8"
      data-testid="my-performance-tier-badge"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <div>
          <p className="eyebrow">本期绩效</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">
            本人绩效档次
          </h2>
        </div>
        {state.kind === 'success' ? (
          <span
            className="text-xs"
            style={{ color: 'var(--color-steel)' }}
            data-testid="tier-data-updated-at"
          >
            {formatTimestamp(state.data.data_updated_at)}
          </span>
        ) : null}
      </div>

      {state.kind === 'loading' ? <SkeletonRows /> : null}
      {state.kind === 'success' ? <TierContent data={state.data} /> : null}
      {state.kind === 'unbound' ? <UnboundCard /> : null}
      {state.kind === 'employee_missing' ? <EmployeeMissingCard /> : null}
      {state.kind === 'error' ? <ErrorCard message={state.message} onRetry={load} /> : null}
    </section>
  );
}

function SkeletonRows() {
  return (
    <div className="mt-4 space-y-3" aria-busy="true" data-testid="tier-skeleton-rows">
      {[0, 1].map((i) => (
        <div
          key={i}
          className="surface-subtle px-5 py-4 animate-pulse"
          style={{ height: i === 0 ? 72 : 48, opacity: 0.6 }}
        />
      ))}
    </div>
  );
}

function TierContent({ data }: { data: MyTierResponse }) {
  const visual = resolveTierVisual(data);

  return (
    <div className="mt-4 space-y-4">
      <div
        className="surface-subtle px-5 py-5"
        data-testid="my-tier-summary-card"
      >
        <span
          className="status-pill"
          data-testid={`my-tier-badge-${data.tier ?? data.reason ?? 'unknown'}`}
          style={{
            background: visual.bg,
            color: visual.color,
            fontSize: 15,
            padding: '7px 14px',
          }}
        >
          {visual.label}
        </span>
        {visual.description ? (
          <p
            className="mt-3 text-sm leading-7"
            style={{ color: 'var(--color-steel)' }}
            data-testid="my-tier-description"
          >
            {visual.description}
          </p>
        ) : null}
        {data.tier != null && data.year != null ? (
          <p
            className="mt-2 text-sm"
            style={{ color: 'var(--color-steel)' }}
            data-testid="my-tier-year-note"
          >
            {data.year} 年度档次（按全公司 20/70/10 分档）
          </p>
        ) : null}
      </div>
    </div>
  );
}

function resolveTierVisual(data: MyTierResponse): TierVisualConfig {
  if (data.tier === 1) {
    return {
      bg: '#d1fae5',
      color: '#065f46',
      label: '1 档',
      description: null,
    };
  }
  if (data.tier === 2) {
    return {
      bg: '#fef3c7',
      color: '#92400e',
      label: '2 档',
      description: null,
    };
  }
  if (data.tier === 3) {
    return {
      bg: '#ffedd5',
      color: '#9a3412',
      label: '3 档',
      description: null,
    };
  }
  if (data.reason === 'insufficient_sample') {
    return {
      bg: '#f3f4f6',
      color: '#6b7280',
      label: '暂不分档',
      description: '本年度全公司绩效样本不足，暂不分档',
    };
  }
  if (data.reason === 'no_snapshot') {
    return {
      bg: '#f3f4f6',
      color: '#6b7280',
      label: '暂无档次',
      description: '本年度尚无档次数据，请等待 HR 录入后查看',
    };
  }
  return {
    bg: '#f3f4f6',
    color: '#6b7280',
    label: '未找到档次',
    description: '未找到您本年度的绩效记录，如有疑问请联系 HR',
  };
}

function UnboundCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="my-tier-unbound-card"
      style={{ background: '#f3f4f6' }}
    >
      <p className="text-sm text-ink">您的账号尚未绑定员工档案。</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-steel)' }}>
        请前往
        <Link
          to="/settings"
          className="ml-1"
          style={{ color: 'var(--color-primary)' }}
          data-testid="my-tier-unbound-settings-link"
        >
          账号设置
        </Link>
        完成绑定，然后再查看本人绩效档次。
      </p>
    </div>
  );
}

function EmployeeMissingCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="my-tier-employee-missing-card"
      style={{ background: '#fef3c7' }}
    >
      <p className="text-sm text-ink">未找到您的员工档案。</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-steel)' }}>
        您的账号绑定了一个不存在的员工记录，请联系 HR 核对。
      </p>
    </div>
  );
}

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="my-tier-error-card"
      style={{ background: '#fef2f2' }}
    >
      <p className="text-sm" style={{ color: 'var(--color-danger)' }}>
        {message}
      </p>
      <button
        type="button"
        className="chip-button mt-3"
        onClick={onRetry}
        data-testid="my-tier-retry-button"
      >
        重试
      </button>
    </div>
  );
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return '数据从未更新';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) {
      return '数据时间无效';
    }
    const formatter = new Intl.DateTimeFormat('zh-CN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
    return `数据更新于 ${formatter.format(d)}`;
  } catch {
    return '数据时间无效';
  }
}
