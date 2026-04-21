import { useCallback, useEffect, useState } from 'react';

import { SyncLogRow } from '../components/feishu-sync-logs/SyncLogRow';
import { SyncLogDetailDrawer } from '../components/feishu-sync-logs/SyncLogDetailDrawer';
import { SyncLogsEmptyState } from '../components/feishu-sync-logs/SyncLogsEmptyState';
import { SyncLogsTabBar, type TabKey } from '../components/feishu-sync-logs/SyncLogsTabBar';
import { downloadUnmatchedCsv, getSyncLogs } from '../services/feishuService';
import type { SyncLogRead, SyncLogSyncType } from '../types/api';

const PAGE_SIZE = 20;

export function SyncLogsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('all');
  const [page, setPage] = useState(1);
  const [logs, setLogs] = useState<SyncLogRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerLog, setDrawerLog] = useState<SyncLogRead | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const syncType: SyncLogSyncType | undefined =
        activeTab === 'all' ? undefined : activeTab;
      const data = await getSyncLogs({ syncType, page, pageSize: PAGE_SIZE });
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [activeTab, page]);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const handleTabChange = (next: TabKey) => {
    setActiveTab(next);
    setPage(1);
  };

  const handleDownloadCsv = async (log: SyncLogRead) => {
    setDownloadingId(log.id);
    setError(null);
    try {
      await downloadUnmatchedCsv(log.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? `未匹配工号导出失败：${err.message}。请稍后重试。`
          : '未匹配工号导出失败：未知错误。请稍后重试。',
      );
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <main className="app-main" style={{ padding: '20px 24px 32px' }}>
      <header className="section-head mb-4">
        <div>
          <div className="eyebrow">飞书集成 / SYNC OBSERVABILITY</div>
          <h1 className="page-title">飞书同步日志</h1>
          <p className="page-desc">
            查看每次飞书同步的结果与明细，可按类型筛选、下载未匹配工号 CSV 自助诊断。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchLogs()}
          className="chip-button"
        >
          刷新列表
        </button>
      </header>

      <SyncLogsTabBar activeTab={activeTab} onChange={handleTabChange} />

      <section className="surface mt-4">
        {error && (
          <div
            role="alert"
            className="mb-2 text-sm"
            style={{ color: 'var(--color-danger)' }}
          >
            同步日志加载失败：{error}。请刷新重试，或联系管理员确认后端服务状态。
          </div>
        )}
        {loading && (
          <div
            className="p-4 text-sm"
            style={{ color: 'var(--color-steel)' }}
          >
            正在加载同步日志...
          </div>
        )}
        {!loading && logs.length === 0 && !error && <SyncLogsEmptyState />}
        {!loading && logs.length > 0 && (
          <table className="w-full text-left" aria-live="polite">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  同步类型
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  状态
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  模式
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  计数
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  触发时间
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  耗时
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  触发人
                </th>
                <th
                  className="px-3 py-2 text-sm font-semibold"
                  style={{ color: 'var(--color-steel)' }}
                >
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <SyncLogRow
                  key={log.id}
                  log={log}
                  onOpenDetail={setDrawerLog}
                  onDownloadCsv={handleDownloadCsv}
                  isDownloadingCsv={downloadingId === log.id}
                />
              ))}
            </tbody>
          </table>
        )}
        {logs.length > 0 && (
          <nav
            className="mt-4 flex items-center justify-center gap-4 text-sm"
            style={{ color: 'var(--color-steel)' }}
          >
            <button
              type="button"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="underline"
              style={{
                cursor: page === 1 ? 'not-allowed' : 'pointer',
                opacity: page === 1 ? 0.5 : 1,
                background: 'transparent',
                border: 'none',
                padding: 0,
                color: 'var(--color-steel)',
              }}
            >
              &lt; 上一页
            </button>
            <span>第 {page} 页</span>
            <button
              type="button"
              disabled={logs.length < PAGE_SIZE}
              onClick={() => setPage((p) => p + 1)}
              className="underline"
              style={{
                cursor: logs.length < PAGE_SIZE ? 'not-allowed' : 'pointer',
                opacity: logs.length < PAGE_SIZE ? 0.5 : 1,
                background: 'transparent',
                border: 'none',
                padding: 0,
                color: 'var(--color-steel)',
              }}
            >
              下一页 &gt;
            </button>
          </nav>
        )}
      </section>

      <SyncLogDetailDrawer
        open={drawerLog !== null}
        log={drawerLog}
        onClose={() => setDrawerLog(null)}
      />
    </main>
  );
}
