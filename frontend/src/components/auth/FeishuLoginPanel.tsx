import { useCallback, useEffect, useRef, useState } from 'react';

import { authorizeFeishu } from '../../services/auth';
import { resolveFeishuError, type FeishuError } from '../../utils/feishuErrors';

const QR_SDK_URL =
  'https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js';
const QR_CONTAINER_ID = 'feishu-qr-container';
const QR_EXPIRY_MS = 180_000;

interface QRLoginConfig {
  id: string;
  goto: string;
  width?: string | number;
  height?: string | number;
  style?: string;
}

interface QRLoginInstance {
  matchOrigin: (origin: string) => boolean;
  matchData: (data: unknown) => boolean;
}

declare global {
  interface Window {
    QRLogin?: (cfg: QRLoginConfig) => QRLoginInstance;
  }
}

/** 单例注入飞书 QR SDK 脚本。D-03 策略：cleanup 中不移除 <script> 节点。 */
function useFeishuSdk(): { ready: boolean; error: Error | null; retry: () => void } {
  const [ready, setReady] = useState<boolean>(
    () => typeof window !== 'undefined' && !!window.QRLogin,
  );
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setError(null);
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    if (window.QRLogin) {
      setReady(true);
      return;
    }

    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${QR_SDK_URL}"]`,
    );
    if (existing) {
      if (window.QRLogin) {
        setReady(true);
        return;
      }
      const handleExistingLoad = () => setReady(true);
      const handleExistingError = () => setError(new Error('sdk_load_failed'));
      existing.addEventListener('load', handleExistingLoad, { once: true });
      existing.addEventListener('error', handleExistingError, { once: true });
      return () => {
        existing.removeEventListener('load', handleExistingLoad);
        existing.removeEventListener('error', handleExistingError);
      };
    }

    const script = document.createElement('script');
    script.src = QR_SDK_URL;
    script.async = true;
    const handleLoad = () => setReady(true);
    const handleError = () => setError(new Error('sdk_load_failed'));
    script.addEventListener('load', handleLoad, { once: true });
    script.addEventListener('error', handleError, { once: true });
    document.head.appendChild(script);

    return () => {
      script.removeEventListener('load', handleLoad);
      script.removeEventListener('error', handleError);
      // D-03: 单例策略，不 remove 脚本节点
    };
  }, [attempt]);

  return { ready, error, retry };
}

export function FeishuLoginPanel() {
  const { ready: sdkReady, error: sdkError, retry: retrySdk } = useFeishuSdk();
  const [authorizeUrl, setAuthorizeUrl] = useState<string | null>(null);
  const [isLoadingAuthorize, setIsLoadingAuthorize] = useState<boolean>(false);
  const [authorizeError, setAuthorizeError] = useState<FeishuError | null>(null);
  const [isExpired, setIsExpired] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  const messageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null);
  const expiryTimerRef = useRef<number | null>(null);
  const authorizeUrlRef = useRef<string | null>(null);

  // 挂载 + refreshKey 变化时拉取新的 authorize_url
  useEffect(() => {
    let cancelled = false;
    setIsLoadingAuthorize(true);
    setAuthorizeError(null);
    setAuthorizeUrl(null);
    authorizeUrlRef.current = null;

    void authorizeFeishu()
      .then((data) => {
        if (cancelled) return;
        setAuthorizeUrl(data.authorize_url);
        authorizeUrlRef.current = data.authorize_url;
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setAuthorizeError(resolveFeishuError('backend', err));
      })
      .finally(() => {
        if (!cancelled) setIsLoadingAuthorize(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  // SDK + authorize_url 就绪后渲染二维码 + 挂 message listener + 启动 180s 倒计时
  useEffect(() => {
    if (!sdkReady || !authorizeUrl || !window.QRLogin) return;

    // Pitfall 2：每次重建前清空容器，避免二维码叠加
    const container = document.getElementById(QR_CONTAINER_ID);
    if (container) {
      container.innerHTML = '';
    }

    // 清理上一轮的 message listener，避免重复触发
    if (messageHandlerRef.current) {
      window.removeEventListener('message', messageHandlerRef.current);
      messageHandlerRef.current = null;
    }

    const instance = window.QRLogin({
      id: QR_CONTAINER_ID,
      goto: authorizeUrl,
      width: '260',
      height: '260',
      style: 'width:260px;height:260px;border:none',
    });

    const handler = (event: MessageEvent): void => {
      // T-27-02: matchOrigin + matchData 双校验，防跨域仿冒
      if (!instance.matchOrigin(event.origin)) return;
      if (!instance.matchData(event.data)) return;
      // Pitfall 1: SDK 1.0.3 的 event.data 为对象 { tmp_code: string }
      if (typeof event.data !== 'object' || event.data === null) return;
      const tmpCode = (event.data as { tmp_code?: unknown }).tmp_code;
      if (typeof tmpCode !== 'string' || tmpCode.length === 0) return;
      // Pitfall 3: 从 ref 读取最新 authorize_url，避免刷新后旧 closure 污染
      const base = authorizeUrlRef.current ?? authorizeUrl;
      // D-10 勘误：SDK 不会自动跳转，必须手动拼接 tmp_code 并导航
      window.location.href = base + '&tmp_code=' + encodeURIComponent(tmpCode);
    };
    window.addEventListener('message', handler);
    messageHandlerRef.current = handler;

    // Pitfall 5: 启动 180s 倒计时；cleanup 中 clearTimeout
    if (expiryTimerRef.current !== null) {
      window.clearTimeout(expiryTimerRef.current);
    }
    expiryTimerRef.current = window.setTimeout(() => {
      setIsExpired(true);
    }, QR_EXPIRY_MS);

    return () => {
      if (expiryTimerRef.current !== null) {
        window.clearTimeout(expiryTimerRef.current);
        expiryTimerRef.current = null;
      }
      if (messageHandlerRef.current) {
        window.removeEventListener('message', messageHandlerRef.current);
        messageHandlerRef.current = null;
      }
    };
  }, [sdkReady, authorizeUrl]);

  const handleRefresh = useCallback(() => {
    setIsExpired(false);
    setAuthorizeError(null);
    setRefreshKey((n) => n + 1);
  }, []);

  const handleRetrySdk = useCallback(() => {
    retrySdk();
    setRefreshKey((n) => n + 1);
  }, [retrySdk]);

  // SDK 加载失败优先级高于 authorize 失败
  const displayError: FeishuError | null = sdkError
    ? resolveFeishuError('sdk', sdkError)
    : authorizeError;

  return (
    <section
      className="surface-subtle"
      style={{ marginTop: 20, padding: '20px 20px' }}
    >
      <p className="eyebrow">飞书扫码登录</p>
      <h3
        style={{
          marginTop: 8,
          fontSize: 16,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          color: 'var(--color-ink)',
        }}
      >
        打开飞书 App 扫码
      </h3>
      <p style={{ marginTop: 4, fontSize: 13, color: 'var(--color-steel)' }}>
        使用已开通系统权限的工号扫描下方二维码。
      </p>

      {displayError ? (
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
            {displayError.message}
          </p>
          <div style={{ marginTop: 10 }}>
            <button
              className="action-secondary"
              onClick={
                displayError.code === 'sdk_load_failed' ? handleRetrySdk : handleRefresh
              }
              type="button"
            >
              重试
            </button>
          </div>
        </div>
      ) : (
        <div
          style={{
            marginTop: 16,
            position: 'relative',
            width: 260,
            height: 260,
            marginLeft: 'auto',
            marginRight: 'auto',
          }}
        >
          <div
            id={QR_CONTAINER_ID}
            style={{ width: 260, height: 260 }}
          />
          {(!sdkReady || isLoadingAuthorize || !authorizeUrl) && !isExpired ? (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-steel)',
                fontSize: 13,
              }}
            >
              二维码加载中…
            </div>
          ) : null}
          {isExpired ? (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                background: 'rgba(255,255,255,0.75)',
                backdropFilter: 'blur(4px)',
                WebkitBackdropFilter: 'blur(4px)',
              }}
            >
              <p style={{ fontSize: 13, color: 'var(--color-ink)' }}>二维码已过期</p>
              <button className="action-primary" onClick={handleRefresh} type="button">
                点击刷新
              </button>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
