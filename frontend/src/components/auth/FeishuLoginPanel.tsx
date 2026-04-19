import { useCallback, useEffect, useState } from 'react';

import { authorizeFeishu } from '../../services/auth';
import { resolveFeishuError, type FeishuError } from '../../utils/feishuErrors';

/**
 * 飞书账号授权登录面板。
 *
 * 挂载时拉取 authorize_url（含后端生成的 state，Redis TTL 300s），
 * 用户点击「使用飞书账号登录」时整页跳转到飞书授权页完成 OAuth 流程。
 *
 * Phase 27 D-17 amendment：QR 扫码链路因飞书应用能力限制无法启用，
 * 简化为仅保留整页跳转授权。所有 QR SDK / postMessage / 倒计时 / 刷新
 * 逻辑均已移除。
 */
export function FeishuLoginPanel() {
  const [authorizeUrl, setAuthorizeUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<FeishuError | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setAuthorizeUrl(null);

    void authorizeFeishu()
      .then((data) => {
        if (cancelled) return;
        setAuthorizeUrl(data.authorize_url);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(resolveFeishuError('backend', err));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const handleAuthorize = useCallback(() => {
    if (!authorizeUrl) return;
    window.location.href = authorizeUrl;
  }, [authorizeUrl]);

  const handleRetry = useCallback(() => {
    setRefreshKey((n) => n + 1);
  }, []);

  return (
    <section
      className="surface-subtle"
      style={{ marginTop: 20, padding: '20px 20px' }}
    >
      <p className="eyebrow">飞书账号登录</p>
      <h3
        style={{
          marginTop: 8,
          fontSize: 16,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          color: 'var(--color-ink)',
        }}
      >
        使用飞书账号授权登录
      </h3>
      <p style={{ marginTop: 4, fontSize: 13, lineHeight: 1.6, color: 'var(--color-steel)' }}>
        点击下方按钮跳转到飞书授权页，已登录飞书时可直接完成授权。
      </p>

      {error ? (
        <div
          style={{
            marginTop: 16,
            padding: '12px 14px',
            borderRadius: 6,
            border: '1px solid var(--color-border)',
            background: 'var(--color-bg-subtle)',
          }}
        >
          <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--color-danger)' }}>
            {error.message}
          </p>
          <div style={{ marginTop: 10 }}>
            <button className="action-secondary" onClick={handleRetry} type="button">
              重试
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginTop: 16 }}>
          <button
            className="action-primary"
            disabled={isLoading || !authorizeUrl}
            onClick={handleAuthorize}
            type="button"
            style={{ width: '100%' }}
          >
            {isLoading ? '正在准备…' : '使用飞书账号登录 →'}
          </button>
          <p
            style={{
              marginTop: 8,
              fontSize: 12,
              color: 'var(--color-steel)',
              textAlign: 'center',
            }}
          >
            已登录飞书时一键授权，未登录时将进入飞书登录页
          </p>
        </div>
      )}
    </section>
  );
}
