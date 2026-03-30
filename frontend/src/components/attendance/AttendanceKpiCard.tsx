import { useEffect, useState } from 'react';

import { getEmployeeAttendance } from '../../services/attendanceService';
import type { AttendanceSummaryRead } from '../../types/api';

interface AttendanceKpiCardProps {
  employeeId: string;
  period?: string;
}

type CardState = 'loading' | 'never_synced' | 'no_data' | 'stale' | 'normal' | 'error';

const STALE_THRESHOLD_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function formatDataAsOf(isoString: string): string {
  const d = new Date(isoString);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function formatRate(value: number | null): string {
  if (value === null) return '--';
  return `${value.toFixed(1)}%`;
}

function formatDays(value: number | null): string {
  if (value === null) return '--';
  return `${value} 天`;
}

function formatHours(value: number | null): string {
  if (value === null) return '--';
  return `${value.toFixed(1)} h`;
}

function formatCount(value: number | null): string {
  if (value === null) return '--';
  return `${value} 次`;
}

export function AttendanceKpiCard({ employeeId, period }: AttendanceKpiCardProps) {
  const [data, setData] = useState<AttendanceSummaryRead | null>(null);
  const [cardState, setCardState] = useState<CardState>('loading');

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setCardState('loading');
      try {
        const result = await getEmployeeAttendance(employeeId, period, controller.signal);
        if (controller.signal.aborted) return;

        if (result === null) {
          setData(null);
          setCardState('no_data');
          return;
        }

        setData(result);

        const dataAge = Date.now() - new Date(result.data_as_of).getTime();
        if (dataAge > STALE_THRESHOLD_MS) {
          setCardState('stale');
        } else {
          setCardState('normal');
        }
      } catch (err: unknown) {
        if (controller.signal.aborted) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setCardState('error');
      }
    }

    void load();
    return () => {
      controller.abort();
    };
  }, [employeeId, period]);

  if (cardState === 'loading') {
    return (
      <div className="surface px-4 py-4" style={{ opacity: 0.6 }}>
        <p className="eyebrow">考勤概览</p>
        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div className="surface-subtle px-3 py-3" key={i}>
              <p className="metric-label" style={{ fontSize: 12 }}>&nbsp;</p>
              <p className="metric-value" style={{ fontSize: 26, fontWeight: 600 }}>--</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (cardState === 'never_synced' || cardState === 'no_data') {
    return (
      <div className="surface px-4 py-4" style={{ background: 'var(--color-bg-subtle)' }}>
        <p className="eyebrow">考勤概览</p>
        <p className="mt-3 text-sm text-steel">
          {cardState === 'never_synced' ? '暂无考勤数据' : '该员工暂无考勤记录'}
        </p>
      </div>
    );
  }

  if (cardState === 'error') {
    return (
      <div className="surface px-4 py-4" style={{ background: 'var(--color-bg-subtle)' }}>
        <p className="eyebrow">考勤概览</p>
        <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>考勤数据加载失败</p>
      </div>
    );
  }

  const kpis = [
    { label: '出勤率', value: formatRate(data?.attendance_rate ?? null), ariaLabel: `出勤率 ${formatRate(data?.attendance_rate ?? null)}` },
    { label: '缺勤天数', value: formatDays(data?.absence_days ?? null), ariaLabel: `缺勤天数 ${formatDays(data?.absence_days ?? null)}` },
    { label: '加班时长', value: formatHours(data?.overtime_hours ?? null), ariaLabel: `加班时长 ${formatHours(data?.overtime_hours ?? null)}` },
    { label: '迟到次数', value: formatCount(data?.late_count ?? null), ariaLabel: `迟到次数 ${formatCount(data?.late_count ?? null)}` },
    { label: '早退次数', value: formatCount(data?.early_leave_count ?? null), ariaLabel: `早退次数 ${formatCount(data?.early_leave_count ?? null)}` },
  ];

  return (
    <div className="surface px-4 py-4">
      <p className="eyebrow">考勤概览</p>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
        {kpis.map((kpi) => (
          <div className="surface-subtle px-3 py-3" key={kpi.label} aria-label={kpi.ariaLabel}>
            <p className="metric-label" style={{ fontSize: 12 }}>{kpi.label}</p>
            <p className="metric-value" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1.1 }}>{kpi.value}</p>
          </div>
        ))}
      </div>
      {data?.data_as_of ? (
        <p className="metric-note mt-2" style={{ fontSize: 12, color: cardState === 'stale' ? 'var(--color-warning)' : 'var(--color-placeholder)' }}>
          {cardState === 'stale' ? '数据可能已过期 — ' : ''}数据截至：{formatDataAsOf(data.data_as_of)}
        </p>
      ) : null}
    </div>
  );
}
