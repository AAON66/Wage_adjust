import type React from 'react';

import { formatStatusText } from '../../utils/statusText';

const STATUS_LABELS: Record<string, string> = {
  collecting: '收集中',
  submitted: '已提交',
  parsing: '解析中',
  evaluated: '已评估',
  reviewing: '复核中',
  calibrated: '已校准',
  approved: '已审批',
  published: '已发布',
  active: '启用',
  inactive: '停用',
  pending: '待处理',
  completed: '已完成',
  failed: '失败',
  queued: '排队中',
  processing: '处理中',
  rejected: '已驳回',
  parsed: '已解析',
};

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  collecting:  { background: 'var(--color-bg-subtle)',    color: 'var(--color-steel)' },
  submitted:   { background: 'var(--color-info-bg)',      color: 'var(--color-info)' },
  parsing:     { background: 'var(--color-warning-bg)',   color: 'var(--color-warning)' },
  evaluated:   { background: 'var(--color-success-bg)',   color: 'var(--color-success)' },
  reviewing:   { background: 'var(--color-warning-bg)',   color: 'var(--color-warning)' },
  calibrated:  { background: '#EDE9FE',                   color: '#6D28D9' },
  approved:    { background: 'var(--color-success-bg)',   color: 'var(--color-success)' },
  published:   { background: '#EDE9FE',                   color: '#6D28D9' },
  active:      { background: 'var(--color-success-bg)',   color: 'var(--color-success)' },
  inactive:    { background: 'var(--color-bg-subtle)',    color: 'var(--color-steel)' },
  pending:     { background: 'var(--color-warning-bg)',   color: 'var(--color-warning)' },
  completed:   { background: 'var(--color-success-bg)',   color: 'var(--color-success)' },
  failed:      { background: 'var(--color-danger-bg)',    color: 'var(--color-danger)' },
  queued:      { background: 'var(--color-bg-subtle)',    color: 'var(--color-steel)' },
  processing:  { background: 'var(--color-warning-bg)',   color: 'var(--color-warning)' },
  rejected:    { background: 'var(--color-danger-bg)',    color: 'var(--color-danger)' },
  parsed:      { background: 'var(--color-success-bg)',   color: 'var(--color-success)' },
};

const DEFAULT_STYLE: React.CSSProperties = { background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' };

interface StatusIndicatorProps {
  status: string;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const normalized = status.toLowerCase();
  const label = STATUS_LABELS[normalized] ?? formatStatusText(status, status);
  const style = STATUS_STYLES[normalized] ?? DEFAULT_STYLE;

  return <span className="status-pill" style={style}>{label}</span>;
}
