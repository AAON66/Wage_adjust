import { useEffect, useState } from 'react';
import { AppShell } from '../components/layout/AppShell';
import { getAuditLogs } from '../services/auditService';
import type { AuditLogQueryParams } from '../services/auditService';
import type { AuditLogRead } from '../types/api';

const PAGE_LIMIT = 50;

export function AuditLogPage() {
  const [action, setAction] = useState('');
  const [targetType, setTargetType] = useState('');
  const [operatorId, setOperatorId] = useState('');
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');
  const [items, setItems] = useState<AuditLogRead[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  function buildParams(currentOffset: number): AuditLogQueryParams {
    const params: AuditLogQueryParams = { limit: PAGE_LIMIT, offset: currentOffset };
    if (action.trim()) params.action = action.trim();
    if (targetType.trim()) params.target_type = targetType.trim();
    if (operatorId.trim()) params.operator_id = operatorId.trim();
    if (fromDt) params.from_dt = new Date(fromDt).toISOString();
    if (toDt) params.to_dt = new Date(toDt).toISOString();
    return params;
  }

  async function fetchLogs(currentOffset: number) {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await getAuditLogs(buildParams(currentOffset));
      setItems(data.items);
      setTotal(data.total);
      setOffset(currentOffset);
    } catch {
      setErrorMsg('加载审计日志失败，请稍后重试。');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void fetchLogs(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleQuery() {
    void fetchLogs(0);
  }

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_LIMIT < total;

  return (
    <AppShell title="审计日志" description="查看所有操作记录">
      <section className="surface animate-fade-up px-6 py-5">
        <div className="flex flex-wrap gap-3">
          <input
            className="input-field w-40"
            onChange={(e) => setAction(e.target.value)}
            placeholder="操作类型"
            type="text"
            value={action}
          />
          <input
            className="input-field w-40"
            onChange={(e) => setTargetType(e.target.value)}
            placeholder="实体类型"
            type="text"
            value={targetType}
          />
          <input
            className="input-field w-52"
            onChange={(e) => setOperatorId(e.target.value)}
            placeholder="操作人 ID"
            type="text"
            value={operatorId}
          />
          <input
            className="input-field w-52"
            onChange={(e) => setFromDt(e.target.value)}
            title="开始时间"
            type="datetime-local"
            value={fromDt}
          />
          <input
            className="input-field w-52"
            onChange={(e) => setToDt(e.target.value)}
            title="结束时间"
            type="datetime-local"
            value={toDt}
          />
          <button className="action-primary" onClick={handleQuery} type="button">
            查询
          </button>
        </div>
      </section>

      <section className="surface animate-fade-up mt-4 px-6 py-5">
        {isLoading ? (
          <p className="text-sm text-steel">加载中...</p>
        ) : errorMsg ? (
          <p className="text-sm" style={{ color: 'var(--color-danger)' }}>{errorMsg}</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-steel" style={{ borderColor: 'var(--color-border)' }}>
                    <th className="pb-2 pr-4 font-medium">时间</th>
                    <th className="pb-2 pr-4 font-medium">操作类型</th>
                    <th className="pb-2 pr-4 font-medium">实体类型</th>
                    <th className="pb-2 pr-4 font-medium">实体 ID</th>
                    <th className="pb-2 pr-4 font-medium">操作人 ID</th>
                    <th className="pb-2 pr-4 font-medium">操作人角色</th>
                    <th className="pb-2 pr-4 font-medium">请求 ID</th>
                    <th className="pb-2 font-medium">详情</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td className="pt-4 text-steel" colSpan={8}>暂无记录</td>
                    </tr>
                  ) : (
                    items.map((row) => {
                      const detailStr = JSON.stringify(row.detail);
                      const detailShort = detailStr.length > 80 ? detailStr.slice(0, 80) + '…' : detailStr;
                      return (
                        <tr
                          className="border-b"
                          key={row.id}
                          style={{ borderColor: 'var(--color-border)' }}
                        >
                          <td className="py-2 pr-4 text-steel">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                          <td className="py-2 pr-4 font-medium text-ink">{row.action}</td>
                          <td className="py-2 pr-4 text-steel">{row.target_type}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-steel">{row.target_id}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-steel">{row.operator_id ?? '—'}</td>
                          <td className="py-2 pr-4 text-steel">{row.operator_role ?? '—'}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-steel">{row.request_id ?? '—'}</td>
                          <td className="py-2 text-xs text-steel" title={detailStr}>{detailShort}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex items-center justify-between gap-4">
              <p className="text-sm text-steel">共 {total} 条</p>
              <div className="flex gap-2">
                <button
                  className="action-secondary"
                  disabled={!hasPrev}
                  onClick={() => void fetchLogs(offset - PAGE_LIMIT)}
                  type="button"
                >
                  上一页
                </button>
                <button
                  className="action-secondary"
                  disabled={!hasNext}
                  onClick={() => void fetchLogs(offset + PAGE_LIMIT)}
                  type="button"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
