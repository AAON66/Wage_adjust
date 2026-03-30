import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { registerWebhook, listWebhooks, unregisterWebhook, getWebhookLogs } from '../services/webhookService';
import type { WebhookEndpointRead, WebhookDeliveryLogRead } from '../types/api';

type ModalState =
  | { kind: 'none' }
  | { kind: 'register' }
  | { kind: 'confirm-deactivate'; webhookId: string; webhookUrl: string }
  | { kind: 'logs'; webhookId: string; webhookUrl: string };

const AVAILABLE_EVENTS = ['recommendation.approved'];

function formatDateTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export function WebhookManagementPage() {
  const [webhooks, setWebhooks] = useState<WebhookEndpointRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState>({ kind: 'none' });
  const [isBusy, setIsBusy] = useState(false);

  // Register form state
  const [regUrl, setRegUrl] = useState('');
  const [regDescription, setRegDescription] = useState('');
  const [regEvents, setRegEvents] = useState<string[]>(['recommendation.approved']);

  // Logs state
  const [logs, setLogs] = useState<WebhookDeliveryLogRead[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  async function loadWebhooks() {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await listWebhooks();
      setWebhooks(data);
    } catch {
      setErrorMsg('加载 Webhook 列表失败');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadWebhooks();
  }, []);

  function openRegisterModal() {
    setRegUrl('');
    setRegDescription('');
    setRegEvents(['recommendation.approved']);
    setModal({ kind: 'register' });
  }

  async function handleRegister() {
    if (!regUrl.trim()) return;
    setIsBusy(true);
    setErrorMsg(null);
    try {
      await registerWebhook({
        url: regUrl.trim(),
        description: regDescription.trim() || undefined,
        events: regEvents,
      });
      setModal({ kind: 'none' });
      void loadWebhooks();
    } catch {
      setErrorMsg('注册 Webhook 失败');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDeactivate(webhookId: string) {
    setIsBusy(true);
    setErrorMsg(null);
    try {
      await unregisterWebhook(webhookId);
      setModal({ kind: 'none' });
      void loadWebhooks();
    } catch {
      setErrorMsg('停用 Webhook 失败');
    } finally {
      setIsBusy(false);
    }
  }

  async function openLogs(webhookId: string, webhookUrl: string) {
    setModal({ kind: 'logs', webhookId, webhookUrl });
    setLogsLoading(true);
    try {
      const data = await getWebhookLogs(webhookId);
      setLogs(data);
    } catch {
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }

  function toggleEvent(event: string) {
    setRegEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  }

  return (
    <AppShell
      title="Webhook 管理"
      description="注册回调 URL，查看通知投递日志。"
      actions={
        <button className="action-primary" onClick={openRegisterModal} type="button">
          注册新 Webhook
        </button>
      }
    >
      {errorMsg ? (
        <div className="surface px-5 py-3" style={{ color: 'var(--color-danger)' }}>
          <p className="text-sm">{errorMsg}</p>
        </div>
      ) : null}

      {/* Webhook list */}
      <div className="surface px-6 py-5 lg:px-7">
        {isLoading ? (
          <p className="text-sm text-steel" style={{ textAlign: 'center', padding: 24 }}>正在加载...</p>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-steel" style={{ textAlign: 'center', padding: 24 }}>暂无 Webhook，请点击「注册新 Webhook」添加。</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>URL</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>描述</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>事件类型</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>状态</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>创建时间</th>
                  <th style={{ textAlign: 'right', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {webhooks.map((w) => (
                  <tr key={w.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px', fontFamily: 'monospace', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.url}</td>
                    <td style={{ padding: '10px' }}>{w.description ?? '-'}</td>
                    <td style={{ padding: '10px' }}>
                      <span style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 4 }}>
                        {w.events.map((ev) => (
                          <span key={ev} style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 4, fontSize: 11, fontWeight: 500, background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>{ev}</span>
                        ))}
                      </span>
                    </td>
                    <td style={{ padding: '10px' }}>
                      {w.is_active ? (
                        <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600, background: 'var(--color-success-light, #f6ffed)', color: 'var(--color-success, #52c41a)' }}>活跃</span>
                      ) : (
                        <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600, background: 'var(--color-danger-light, #fff1f0)', color: 'var(--color-danger, #f5222d)' }}>已停用</span>
                      )}
                    </td>
                    <td style={{ padding: '10px' }}>{formatDateTime(w.created_at)}</td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>
                      <span style={{ display: 'inline-flex', gap: 6 }}>
                        <button
                          className="chip-button"
                          onClick={() => void openLogs(w.id, w.url)}
                          type="button"
                        >
                          查看日志
                        </button>
                        {w.is_active ? (
                          <button
                            className="chip-button"
                            onClick={() => setModal({ kind: 'confirm-deactivate', webhookId: w.id, webhookUrl: w.url })}
                            style={{ color: 'var(--color-danger)' }}
                            type="button"
                          >
                            停用
                          </button>
                        ) : null}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Register modal */}
      {modal.kind === 'register' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 480, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>注册 Webhook</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>URL *</label>
                <input
                  className="toolbar-input"
                  style={{ width: '100%' }}
                  type="url"
                  value={regUrl}
                  onChange={(e) => setRegUrl(e.target.value)}
                  placeholder="https://your-system.example.com/webhook"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>描述（可选）</label>
                <input
                  className="toolbar-input"
                  style={{ width: '100%' }}
                  type="text"
                  value={regDescription}
                  onChange={(e) => setRegDescription(e.target.value)}
                  placeholder="例如: HR 系统调薪通知"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>事件类型</label>
                {AVAILABLE_EVENTS.map((ev) => (
                  <label key={ev} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={regEvents.includes(ev)}
                      onChange={() => toggleEvent(ev)}
                    />
                    {ev}
                  </label>
                ))}
              </div>
            </div>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">取消</button>
              <button className="action-primary" disabled={isBusy || !regUrl.trim()} onClick={() => void handleRegister()} type="button">
                {isBusy ? '注册中...' : '注册'}
              </button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}

      {/* Confirm deactivate modal */}
      {modal.kind === 'confirm-deactivate' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 400, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>确认停用</h3>
            <p style={{ fontSize: 13, color: 'var(--color-steel)', lineHeight: 1.6 }}>
              确定要停用此 Webhook 吗？停用后将不再向此 URL 发送通知。
            </p>
            <p style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--color-ink)', marginTop: 8, wordBreak: 'break-all' }}>{modal.webhookUrl}</p>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">取消</button>
              <button
                className="action-primary"
                disabled={isBusy}
                onClick={() => void handleDeactivate(modal.webhookId)}
                style={{ background: 'var(--color-danger)' }}
                type="button"
              >
                {isBusy ? '停用中...' : '确认停用'}
              </button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}

      {/* Logs modal */}
      {modal.kind === 'logs' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 700, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>投递日志</h3>
            <p style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--color-steel)', marginBottom: 16, wordBreak: 'break-all' }}>{modal.webhookUrl}</p>
            {logsLoading ? (
              <p className="text-sm text-steel" style={{ padding: 16, textAlign: 'center' }}>加载中...</p>
            ) : logs.length === 0 ? (
              <p className="text-sm text-steel" style={{ padding: 16, textAlign: 'center' }}>暂无投递记录。</p>
            ) : (
              <div style={{ overflowX: 'auto', maxHeight: 400, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>事件类型</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>时间</th>
                      <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>HTTP 状态</th>
                      <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>尝试次数</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>结果</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--color-steel)' }}>错误信息</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr
                        key={log.id}
                        style={{
                          borderBottom: '1px solid var(--color-border)',
                          background: log.success ? 'var(--color-success-light, #f6ffed)' : 'var(--color-danger-light, #fff1f0)',
                        }}
                      >
                        <td style={{ padding: '8px' }}>{log.event_type}</td>
                        <td style={{ padding: '8px' }}>{formatDateTime(log.created_at)}</td>
                        <td style={{ padding: '8px', textAlign: 'right' }}>{log.response_status ?? '-'}</td>
                        <td style={{ padding: '8px', textAlign: 'right' }}>{log.attempt}</td>
                        <td style={{ padding: '8px' }}>
                          {log.success ? (
                            <span style={{ color: 'var(--color-success, #52c41a)', fontWeight: 600 }}>成功</span>
                          ) : (
                            <span style={{ color: 'var(--color-danger, #f5222d)', fontWeight: 600 }}>失败</span>
                          )}
                        </td>
                        <td style={{ padding: '8px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {log.error_message ?? '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">关闭</button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}

function ModalOverlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="surface"
        style={{ padding: '24px 28px', borderRadius: 10, maxHeight: '90vh', overflowY: 'auto' }}
      >
        {children}
      </div>
    </div>
  );
}
