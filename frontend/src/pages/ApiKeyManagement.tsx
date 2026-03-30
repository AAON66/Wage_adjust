import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { createApiKey, listApiKeys, rotateApiKey, revokeApiKey } from '../services/apiKeyService';
import type { ApiKeyRead } from '../types/api';

type ModalState =
  | { kind: 'none' }
  | { kind: 'create' }
  | { kind: 'show-key'; plainKey: string }
  | { kind: 'confirm-rotate'; keyId: string; keyName: string }
  | { kind: 'confirm-revoke'; keyId: string; keyName: string };

function formatDateTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function KeyStatusBadge({ item }: { item: ApiKeyRead }) {
  if (!item.is_active) {
    return <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600, background: 'var(--color-danger-light, #fff1f0)', color: 'var(--color-danger, #f5222d)' }}>已撤销</span>;
  }
  if (item.expires_at && new Date(item.expires_at) < new Date()) {
    return <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600, background: '#fff7e6', color: '#d46b08' }}>已过期</span>;
  }
  return <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600, background: 'var(--color-success-light, #f6ffed)', color: 'var(--color-success, #52c41a)' }}>活跃</span>;
}

export function ApiKeyManagementPage() {
  const [keys, setKeys] = useState<ApiKeyRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState>({ kind: 'none' });
  const [isBusy, setIsBusy] = useState(false);

  // Create form state
  const [createName, setCreateName] = useState('');
  const [createRateLimit, setCreateRateLimit] = useState(1000);
  const [createExpiresAt, setCreateExpiresAt] = useState('');

  async function loadKeys() {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await listApiKeys();
      setKeys(data);
    } catch {
      setErrorMsg('加载 API Key 列表失败');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadKeys();
  }, []);

  function openCreateModal() {
    setCreateName('');
    setCreateRateLimit(1000);
    setCreateExpiresAt('');
    setModal({ kind: 'create' });
  }

  async function handleCreate() {
    if (!createName.trim()) return;
    setIsBusy(true);
    setErrorMsg(null);
    try {
      const result = await createApiKey({
        name: createName.trim(),
        rate_limit: createRateLimit,
        expires_at: createExpiresAt || null,
      });
      setModal({ kind: 'show-key', plainKey: result.plain_key });
      void loadKeys();
    } catch {
      setErrorMsg('创建 API Key 失败');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRotate(keyId: string) {
    setIsBusy(true);
    setErrorMsg(null);
    try {
      const result = await rotateApiKey(keyId);
      setModal({ kind: 'show-key', plainKey: result.plain_key });
      void loadKeys();
    } catch {
      setErrorMsg('轮换 API Key 失败');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRevoke(keyId: string) {
    setIsBusy(true);
    setErrorMsg(null);
    try {
      await revokeApiKey(keyId);
      setModal({ kind: 'none' });
      void loadKeys();
    } catch {
      setErrorMsg('撤销 API Key 失败');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCopyKey(plainKey: string) {
    try {
      await navigator.clipboard.writeText(plainKey);
    } catch {
      // Fallback: select text in the input
    }
  }

  return (
    <AppShell
      title="API Key 管理"
      description="创建、查看、轮换和撤销外部 API 访问密钥。"
      actions={
        <button className="action-primary" onClick={openCreateModal} type="button">
          创建新 Key
        </button>
      }
    >
      {errorMsg ? (
        <div className="surface px-5 py-3" style={{ color: 'var(--color-danger)' }}>
          <p className="text-sm">{errorMsg}</p>
        </div>
      ) : null}

      {/* Key list */}
      <div className="surface px-6 py-5 lg:px-7">
        {isLoading ? (
          <p className="text-sm text-steel" style={{ textAlign: 'center', padding: 24 }}>正在加载...</p>
        ) : keys.length === 0 ? (
          <p className="text-sm text-steel" style={{ textAlign: 'center', padding: 24 }}>暂无 API Key，请点击「创建新 Key」添加。</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>名称</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>Key 前缀</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>状态</th>
                  <th style={{ textAlign: 'right', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>限流/时</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>创建时间</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>最后使用</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>最后 IP</th>
                  <th style={{ textAlign: 'right', padding: '8px 10px', fontWeight: 600, color: 'var(--color-steel)' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px' }}>{k.name}</td>
                    <td style={{ padding: '10px', fontFamily: 'monospace' }}>{k.key_prefix}...</td>
                    <td style={{ padding: '10px' }}><KeyStatusBadge item={k} /></td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>{k.rate_limit}</td>
                    <td style={{ padding: '10px' }}>{formatDateTime(k.created_at)}</td>
                    <td style={{ padding: '10px' }}>{formatDateTime(k.last_used_at)}</td>
                    <td style={{ padding: '10px', fontFamily: 'monospace' }}>{k.last_used_ip ?? '-'}</td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>
                      {k.is_active ? (
                        <span style={{ display: 'inline-flex', gap: 6 }}>
                          <button
                            className="chip-button"
                            onClick={() => setModal({ kind: 'confirm-rotate', keyId: k.id, keyName: k.name })}
                            type="button"
                          >
                            轮换
                          </button>
                          <button
                            className="chip-button"
                            onClick={() => setModal({ kind: 'confirm-revoke', keyId: k.id, keyName: k.name })}
                            style={{ color: 'var(--color-danger)' }}
                            type="button"
                          >
                            撤销
                          </button>
                        </span>
                      ) : (
                        <span className="text-steel" style={{ fontSize: 12 }}>-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {modal.kind === 'create' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 440, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>创建 API Key</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>名称 *</label>
                <input
                  className="toolbar-input"
                  style={{ width: '100%' }}
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="例如: HR 系统对接"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>每小时限流</label>
                <input
                  className="toolbar-input"
                  style={{ width: '100%' }}
                  type="number"
                  min={1}
                  value={createRateLimit}
                  onChange={(e) => setCreateRateLimit(Number(e.target.value))}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>过期时间（可选）</label>
                <input
                  className="toolbar-input"
                  style={{ width: '100%' }}
                  type="datetime-local"
                  value={createExpiresAt}
                  onChange={(e) => setCreateExpiresAt(e.target.value)}
                />
              </div>
            </div>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">取消</button>
              <button className="action-primary" disabled={isBusy || !createName.trim()} onClick={() => void handleCreate()} type="button">
                {isBusy ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}

      {modal.kind === 'show-key' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 520, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>API Key 已生成</h3>
            <p style={{ fontSize: 13, color: 'var(--color-danger)', fontWeight: 600, marginBottom: 14 }}>
              请立即复制此 Key，关闭后将无法再次查看。
            </p>
            <div style={{ position: 'relative' }}>
              <input
                readOnly
                className="toolbar-input"
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 13, paddingRight: 72 }}
                type="text"
                value={modal.plainKey}
                onFocus={(e) => e.target.select()}
              />
              <button
                className="chip-button"
                style={{ position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)' }}
                onClick={() => void handleCopyKey(modal.plainKey)}
                type="button"
              >
                复制
              </button>
            </div>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
              <button className="action-primary" onClick={() => setModal({ kind: 'none' })} type="button">
                我已复制，关闭
              </button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}

      {modal.kind === 'confirm-rotate' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 400, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>确认轮换</h3>
            <p style={{ fontSize: 13, color: 'var(--color-steel)', lineHeight: 1.6 }}>
              确定要轮换 Key「{modal.keyName}」吗？旧 Key 将立即失效。
            </p>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">取消</button>
              <button className="action-primary" disabled={isBusy} onClick={() => void handleRotate(modal.keyId)} type="button">
                {isBusy ? '轮换中...' : '确认轮换'}
              </button>
            </div>
          </div>
        </ModalOverlay>
      ) : null}

      {modal.kind === 'confirm-revoke' ? (
        <ModalOverlay onClose={() => setModal({ kind: 'none' })}>
          <div style={{ maxWidth: 400, width: '100%' }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>确认撤销</h3>
            <p style={{ fontSize: 13, color: 'var(--color-steel)', lineHeight: 1.6 }}>
              确定要撤销 Key「{modal.keyName}」吗？撤销后立即失效，无法恢复。
            </p>
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="action-secondary" onClick={() => setModal({ kind: 'none' })} type="button">取消</button>
              <button
                className="action-primary"
                disabled={isBusy}
                onClick={() => void handleRevoke(modal.keyId)}
                style={{ background: 'var(--color-danger)' }}
                type="button"
              >
                {isBusy ? '撤销中...' : '确认撤销'}
              </button>
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
