import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { bindFeishu } from '../services/auth';
import { resolveFeishuError } from '../utils/feishuErrors';

type CallbackState = 'processing' | 'success' | 'failed';

export function FeishuBindCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshProfile } = useAuth();
  const [state, setState] = useState<CallbackState>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const hasRunRef = useRef(false);

  useEffect(() => {
    // Guarded mount-once (same pattern as FeishuCallbackPage T-27-03):
    // React StrictMode double-mount protection + prevent re-runs caused by
    // AuthProvider re-renders changing the useAuth / useNavigate refs.
    if (hasRunRef.current) return;
    hasRunRef.current = true;

    const code = searchParams.get('code');
    const stateParam = searchParams.get('state');

    if (!code || !stateParam) {
      setState('failed');
      setErrorMessage(resolveFeishuError('backend', new Error('缺少授权参数')).message);
      return;
    }

    void (async () => {
      try {
        await bindFeishu(code, stateParam);
        await refreshProfile();
        setState('success');
        navigate('/settings', { replace: true, state: { bindSuccess: true } });
      } catch (err) {
        setState('failed');
        setErrorMessage(resolveFeishuError('backend', err).message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-page)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 20px',
      }}
    >
      <section
        className="surface animate-fade-up"
        style={{ padding: '32px 32px', maxWidth: 420, width: '100%', textAlign: 'center' }}
      >
        {state === 'processing' ? (
          <>
            <p className="eyebrow">飞书绑定</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              正在完成飞书绑定…
            </h1>
            <p style={{ marginTop: 12, fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>
              正在校验授权，请稍候。
            </p>
          </>
        ) : null}

        {state === 'success' ? (
          <>
            <p className="eyebrow">飞书绑定</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              绑定成功，正在返回设置页…
            </h1>
          </>
        ) : null}

        {state === 'failed' ? (
          <>
            <p className="eyebrow">飞书绑定失败</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              无法完成绑定
            </h1>
            <p
              style={{
                marginTop: 12,
                fontSize: 13,
                lineHeight: 1.7,
                color: 'var(--color-danger)',
              }}
            >
              {errorMessage}
            </p>
            <div style={{ marginTop: 20 }}>
              <button
                className="action-primary"
                onClick={() => navigate('/settings', { replace: true })}
                type="button"
              >
                返回设置
              </button>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
