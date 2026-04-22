import axios from 'axios';
import { Link } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';

import { fetchMyEligibility } from '../../services/eligibilityService';
import type { EligibilityResultWithTimestamp, EligibilityRuleResult } from '../../types/api';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'success'; data: EligibilityResultWithTimestamp }
  | { kind: 'unbound' }
  | { kind: 'employee_missing' }
  | { kind: 'error'; message: string };

/**
 * Phase 32.1 ESELF-01/02/04/05: 员工自助调薪资格 panel
 * - 顶部 4 态徽章（eligible/ineligible/pending/未绑定）
 * - 4 条规则全展开（不折叠），按 status 4 色染色
 * - 右上时间戳「数据更新于 YYYY-MM-DD HH:MM」（zh-CN locale，无秒）
 * - 错误态处理：422 未绑定 / 404 档案缺失 / 500 重试
 *
 * 独立于 employee 匹配 —— panel 直接调 /eligibility/me，由 user.employee_id 决定能否拿到资格。
 * 横向越权天然不可达：fetchMyEligibility 永远调 /me 无参（T-32.1-01 mitigation）。
 */
export function MyEligibilityPanel() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  const load = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const data = await fetchMyEligibility();
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
      setState({ kind: 'error', message: '资格信息暂时不可用，请稍后重试' });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="surface px-6 py-8" data-testid="my-eligibility-panel">
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <div>
          <p className="eyebrow">本期调薪</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">
            本人调薪资格
          </h2>
        </div>
        {state.kind === 'success' ? (
          <span
            className="text-xs"
            style={{ color: 'var(--color-steel)' }}
            data-testid="data-updated-at"
          >
            {formatTimestamp(state.data.data_updated_at)}
          </span>
        ) : null}
      </div>
      {state.kind === 'loading' ? <SkeletonRows /> : null}
      {state.kind === 'success' ? <EligibilityContent data={state.data} /> : null}
      {state.kind === 'unbound' ? <UnboundCard /> : null}
      {state.kind === 'employee_missing' ? <EmployeeMissingCard /> : null}
      {state.kind === 'error' ? <ErrorCard message={state.message} onRetry={load} /> : null}
    </section>
  );
}

function SkeletonRows() {
  return (
    <div className="mt-4 space-y-3" aria-busy="true" data-testid="skeleton-rows">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="surface-subtle px-5 py-4 animate-pulse"
          style={{ height: 56, opacity: 0.6 }}
        />
      ))}
    </div>
  );
}

function EligibilityContent({ data }: { data: EligibilityResultWithTimestamp }) {
  const ineligibleCount = data.rules.filter((r) => r.status === 'ineligible').length;
  const dataMissingCount = data.rules.filter((r) => r.status === 'data_missing').length;
  return (
    <>
      <div className="mt-4">
        <OverallBadge
          status={data.overall_status}
          ineligibleCount={ineligibleCount}
          dataMissingCount={dataMissingCount}
        />
      </div>
      <div className="mt-5 space-y-3" data-testid="rule-rows">
        {data.rules.map((rule) => (
          <RuleRow key={rule.rule_code} rule={rule} />
        ))}
      </div>
    </>
  );
}

function OverallBadge({
  status,
  ineligibleCount,
  dataMissingCount,
}: {
  status: 'eligible' | 'ineligible' | 'pending';
  ineligibleCount: number;
  dataMissingCount: number;
}) {
  const config = {
    eligible: { bg: '#d1fae5', color: '#065f46', label: '✓ 调薪资格合格' },
    ineligible: {
      bg: '#fee2e2',
      color: '#991b1b',
      label: `✗ 调薪资格不合格（${ineligibleCount} 项未通过）`,
    },
    pending: {
      bg: '#fef3c7',
      color: '#92400e',
      label: `⏳ 资格待定（${dataMissingCount} 项数据缺失）`,
    },
  }[status];
  return (
    <span
      className="status-pill"
      data-testid={`overall-badge-${status}`}
      style={{
        background: config.bg,
        color: config.color,
        fontSize: 14,
        padding: '6px 12px',
      }}
    >
      {config.label}
    </span>
  );
}

const RULE_STATUS_CONFIG: Record<
  EligibilityRuleResult['status'],
  { borderColor: string; badgeBg: string; badgeColor: string; badgeLabel: string }
> = {
  eligible: {
    borderColor: '#10b981',
    badgeBg: '#d1fae5',
    badgeColor: '#065f46',
    badgeLabel: '通过',
  },
  ineligible: {
    borderColor: '#ef4444',
    badgeBg: '#fee2e2',
    badgeColor: '#991b1b',
    badgeLabel: '未通过',
  },
  data_missing: {
    borderColor: '#9ca3af',
    badgeBg: '#e5e7eb',
    badgeColor: '#374151',
    badgeLabel: '数据缺失',
  },
  overridden: {
    borderColor: '#3b82f6',
    badgeBg: '#dbeafe',
    badgeColor: '#1e40af',
    badgeLabel: '已覆盖',
  },
};

function RuleRow({ rule }: { rule: EligibilityRuleResult }) {
  const cfg = RULE_STATUS_CONFIG[rule.status];
  return (
    <div
      className="surface-subtle px-5 py-4"
      data-testid={`rule-row-${rule.rule_code}`}
      style={{
        borderLeft: `4px solid ${cfg.borderColor}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
      }}
    >
      <div style={{ flex: 1 }}>
        <p className="text-base font-semibold text-ink">{rule.rule_label}</p>
        <p className="mt-1 text-sm" style={{ color: 'var(--color-steel)' }}>
          {rule.detail}
        </p>
      </div>
      <span
        className="status-pill"
        style={{
          background: cfg.badgeBg,
          color: cfg.badgeColor,
          fontSize: 12,
          padding: '4px 10px',
        }}
      >
        {cfg.badgeLabel}
      </span>
    </div>
  );
}

function UnboundCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="unbound-card"
      style={{ background: '#f3f4f6' }}
    >
      <p className="text-sm text-ink">您的账号尚未绑定员工档案。</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-steel)' }}>
        请前往
        <Link
          to="/settings"
          className="ml-1"
          style={{ color: 'var(--color-primary)' }}
          data-testid="unbound-settings-link"
        >
          账号设置
        </Link>
        完成绑定，然后再查看本人调薪资格。
      </p>
    </div>
  );
}

function EmployeeMissingCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="employee-missing-card"
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
      data-testid="error-card"
      style={{ background: '#fef2f2' }}
    >
      <p className="text-sm" style={{ color: 'var(--color-danger)' }}>
        {message}
      </p>
      <button
        type="button"
        className="chip-button mt-3"
        onClick={onRetry}
        data-testid="retry-button"
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
