import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { AttendanceKpiCard } from '../components/attendance/AttendanceKpiCard';
import { SyncStatusCard } from '../components/attendance/SyncStatusCard';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { listAttendance } from '../services/attendanceService';
import { checkFeishuConfigExists, getLatestSyncStatus, triggerSync } from '../services/feishuService';
import type { AttendanceRecordRead, SyncLogRead } from '../types/api';

const PAGE_SIZE = 12;

export function AttendanceManagementPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [syncStatus, setSyncStatus] = useState<SyncLogRead | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [configExists, setConfigExists] = useState<boolean | null>(null);

  const [records, setRecords] = useState<AttendanceRecordRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refreshSyncStatus() {
    try {
      const status = await getLatestSyncStatus();
      setSyncStatus(status);
      return status;
    } catch {
      // ignore
      return null;
    }
  }

  async function loadRecords() {
    setIsLoading(true);
    try {
      const response = await listAttendance({
        search: search || undefined,
        department: department || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setRecords(response.items);
      setTotal(response.total);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refreshSyncStatus();
    void checkFeishuConfigExists().then(setConfigExists).catch(() => setConfigExists(false));
  }, []);

  useEffect(() => {
    void loadRecords();
  }, [page, search, department]);

  // Poll sync status while syncing
  useEffect(() => {
    if (isSyncing) {
      pollRef.current = setInterval(async () => {
        const status = await refreshSyncStatus();
        if (status && status.status !== 'running') {
          setIsSyncing(false);
          if (status.status === 'success') {
            setSyncMessage(`同步完成，共更新 ${status.synced_count} 条记录。`);
            void loadRecords();
          } else if (status.status === 'failed') {
            setSyncError(status.error_message ?? '同步失败');
          }
        }
      }, 5000);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [isSyncing]);

  async function handleSync(mode: 'full' | 'incremental') {
    if (isSyncing) return;
    if (mode === 'full') {
      const confirmed = window.confirm('全量同步将拉取飞书表格中的全部数据并覆盖现有记录，确定执行？');
      if (!confirmed) return;
    }
    setIsSyncing(true);
    setSyncMessage(null);
    setSyncError(null);
    try {
      await triggerSync(mode);
    } catch (err: unknown) {
      setIsSyncing(false);
      if (err instanceof Error) {
        setSyncError(err.message);
      } else {
        setSyncError('同步触发失败');
      }
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Show empty state if no config
  if (configExists === false) {
    return (
      <AppShell title="考勤管理" description="查看员工考勤数据，手动或定时从飞书同步最新记录。">
        <div className="surface px-6 py-10" style={{ textAlign: 'center' }}>
          <p className="text-lg font-semibold text-ink">飞书考勤未配置</p>
          <p className="mt-2 text-sm text-steel">请前往飞书配置页面填写应用凭证和字段映射。</p>
          {isAdmin ? (
            <Link className="action-primary mt-4 inline-flex" to="/feishu-config">前往配置</Link>
          ) : null}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="考勤管理"
      description="查看员工考勤数据，手动或定时从飞书同步最新记录。"
      actions={
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <button
            className="action-primary"
            disabled={isSyncing}
            onClick={() => handleSync('incremental')}
            type="button"
          >
            {isSyncing ? '同步中...' : '增量同步'}
          </button>
          <button
            className="action-secondary"
            disabled={isSyncing}
            onClick={() => handleSync('full')}
            type="button"
          >
            {isSyncing ? '同步中...' : '全量同步'}
          </button>
          {isAdmin ? (
            <Link className="action-secondary" to="/feishu-config">飞书配置</Link>
          ) : null}
        </div>
      }
    >
      {/* Sync status card - visual anchor */}
      <SyncStatusCard syncStatus={syncStatus} onRefresh={() => void refreshSyncStatus()} />

      {syncMessage ? (
        <div className="surface px-4 py-3" style={{ color: 'var(--color-success, #00B42A)', fontSize: 13.5 }}>
          {syncMessage}
        </div>
      ) : null}
      {syncError ? (
        <div className="surface px-4 py-3" style={{ color: 'var(--color-danger)', fontSize: 13.5 }}>
          同步失败：{syncError}
        </div>
      ) : null}

      {/* Search and filters */}
      <div className="surface px-4 py-3" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        <input
          className="toolbar-input"
          placeholder="按姓名/工号搜索"
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          style={{ minWidth: 200 }}
        />
        <input
          className="toolbar-input"
          placeholder="部门筛选"
          type="text"
          value={department}
          onChange={(e) => { setDepartment(e.target.value); setPage(1); }}
          style={{ minWidth: 140 }}
        />
      </div>

      {/* Attendance cards grid */}
      {isLoading ? (
        <div className="surface px-6 py-10" style={{ textAlign: 'center' }}>
          <p className="text-sm text-steel">正在加载考勤数据...</p>
        </div>
      ) : records.length === 0 ? (
        <div className="surface px-6 py-10" style={{ textAlign: 'center' }}>
          <p className="text-lg font-semibold text-ink">暂无考勤数据</p>
          <p className="mt-2 text-sm text-steel">请先完成飞书配置，然后点击「增量同步」或「全量同步」拉取考勤记录。</p>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
            {records.map((record) => (
              <div key={record.id}>
                <div className="surface px-4 py-3" style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <p className="text-sm font-semibold text-ink">{record.employee_no}</p>
                  <p className="text-xs text-steel">{record.period}</p>
                </div>
                <AttendanceKpiCard employeeId={record.employee_id} period={record.period} />
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 ? (
            <div className="surface px-4 py-3" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <button
                className="chip-button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                type="button"
              >
                上一页
              </button>
              <span className="text-sm text-steel">
                第 {page} / {totalPages} 页 (共 {total} 条)
              </span>
              <button
                className="chip-button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                type="button"
              >
                下一页
              </button>
            </div>
          ) : null}
        </>
      )}
    </AppShell>
  );
}

export default AttendanceManagementPage;
