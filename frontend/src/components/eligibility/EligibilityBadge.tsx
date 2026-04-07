import { useEffect, useState } from 'react';
import { fetchEmployeeEligibility } from '../../services/eligibilityService';
import type { EligibilityResult } from '../../types/api';

interface EligibilityBadgeProps {
  employeeId: string;
  userRole: string | undefined;
}

// Overall badge pill colors (3-state) -- matches EligibilityListTab.tsx STATUS_BADGE
const BADGE_COLORS: Record<string, { label: string; color: string; bg: string }> = {
  eligible: { label: '\u5408\u683C', color: '#16a34a', bg: '#dcfce7' },
  ineligible: { label: '\u4E0D\u5408\u683C', color: '#dc2626', bg: '#fee2e2' },
  pending: { label: '\u5F85\u5B9A', color: '#ca8a04', bg: '#fef9c3' },
};

// Per-rule status colors (4-state) -- matches EligibilityListTab.tsx RULE_STATUS_BADGE
const RULE_COLORS: Record<string, { label: string; color: string; bg: string }> = {
  eligible: { label: '\u5408\u683C', color: '#16a34a', bg: '#dcfce7' },
  ineligible: { label: '\u4E0D\u5408\u683C', color: '#dc2626', bg: '#fee2e2' },
  data_missing: { label: '\u6570\u636E\u7F3A\u5931', color: '#ca8a04', bg: '#fef9c3' },
  overridden: { label: '\u5DF2\u8986\u76D6', color: '#2563eb', bg: '#dbeafe' },
};

type BadgeState = 'idle' | 'loading' | 'loaded' | 'denied' | 'error';

function RuleIcon({ status, color }: { status: string; color: string }) {
  if (status === 'eligible' || status === 'overridden') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color, flexShrink: 0 }}>
        <path d="M3 8l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === 'ineligible') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color, flexShrink: 0 }}>
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  // data_missing or unknown
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color, flexShrink: 0 }}>
      <path d="M4 8h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function EligibilityBadge({ employeeId, userRole }: EligibilityBadgeProps) {
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const [badgeState, setBadgeState] = useState<BadgeState>('idle');
  const [isExpanded, setIsExpanded] = useState(false);

  const canFetch = !!employeeId && !!userRole && ['admin', 'hrbp', 'manager'].includes(userRole);

  useEffect(() => {
    if (!canFetch) {
      setBadgeState('denied');
      return;
    }
    let cancelled = false;
    setBadgeState('loading');
    fetchEmployeeEligibility(employeeId)
      .then((data) => {
        if (!cancelled) {
          setResult(data);
          setBadgeState('loaded');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          // 403 = role denied (defense in depth), other = network/server error
          const is403 = err?.response?.status === 403;
          setBadgeState(is403 ? 'denied' : 'error');
          setResult(null);
        }
      });
    return () => { cancelled = true; };
  }, [employeeId, userRole, canFetch]);

  // Loading state
  if (badgeState === 'loading') {
    return (
      <div className="surface-subtle px-4 py-4">
        <p className="metric-label">{'\u8C03\u85AA\u8D44\u683C'}</p>
        <p className="mt-2 text-sm text-steel">{'\u52A0\u8F7D\u4E2D...'}</p>
      </div>
    );
  }

  // Error state
  if (badgeState === 'error') {
    return (
      <div className="surface-subtle px-4 py-4">
        <p className="metric-label">{'\u8C03\u85AA\u8D44\u683C'}</p>
        <p className="mt-2 text-sm" style={{ color: 'var(--color-danger)' }}>{'\u52A0\u8F7D\u5931\u8D25'}</p>
      </div>
    );
  }

  // Loaded state with result
  if (badgeState === 'loaded' && result) {
    const colors = BADGE_COLORS[result.overall_status] ?? BADGE_COLORS.pending;
    return (
      <div className="surface-subtle px-4 py-4">
        <p className="metric-label">{'\u8C03\u85AA\u8D44\u683C'}</p>
        <span
          className="status-pill mt-2"
          style={{ backgroundColor: colors.bg, color: colors.color, cursor: 'pointer', display: 'inline-block' }}
          onClick={() => setIsExpanded(!isExpanded)}
          role="button"
          aria-expanded={isExpanded}
        >
          {colors.label}
        </span>
        {isExpanded && result.rules.length > 0 ? (
          <div className="animate-fade-soft" style={{ marginTop: 8, borderRadius: 6, overflow: 'hidden' }}>
            {result.rules.map((rule) => {
              const ruleColors = RULE_COLORS[rule.status] ?? { label: rule.status, color: 'var(--color-steel)', bg: 'transparent' };
              return (
                <div key={rule.rule_code} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', fontSize: 13 }}>
                  <RuleIcon status={rule.status} color={ruleColors.color} />
                  <span style={{ flex: 1 }}>{rule.rule_label}</span>
                  <span style={{ color: ruleColors.color, fontSize: 12 }}>{ruleColors.label}</span>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    );
  }

  // Idle or denied state -- placeholder
  return (
    <div className="surface-subtle px-4 py-4">
      <p className="metric-label">{'\u8C03\u85AA\u8D44\u683C'}</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-placeholder)' }}>{'\u8D44\u683C\u5F85\u68C0'}</p>
    </div>
  );
}
