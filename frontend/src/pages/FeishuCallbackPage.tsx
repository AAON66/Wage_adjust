import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { resolveFeishuError } from '../utils/feishuErrors';
import { getRoleHomePath } from '../utils/roleAccess';

type CallbackState = 'processing' | 'success' | 'failed';

export function FeishuCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithFeishu } = useAuth();
  const [state, setState] = useState<CallbackState>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const hasRunRef = useRef(false);

  useEffect(() => {
    // Guarded mount-once: React StrictMode safety. useAuth/useNavigate refs change
    // on every AuthProvider re-render, so we must NOT depend on them — otherwise
    // effect re-runs cancel the in-flight Promise and state updates are skipped.
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
        const profile = await loginWithFeishu(code, stateParam);
        setState('success');
        if (profile.must_change_password) {
          navigate('/settings', {
            replace: true,
            state: { forcePasswordChange: true, from: getRoleHomePath(profile.role) },
          });
        } else {
          navigate(getRoleHomePath(profile.role), { replace: true });
        }
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
            <p className="eyebrow">飞书登录</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              正在完成飞书登录…
            </h1>
            <p style={{ marginTop: 12, fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>
              正在校验授权，请稍候。
            </p>
          </>
        ) : null}

        {state === 'success' ? (
          <>
            <p className="eyebrow">飞书登录</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              登录成功，正在跳转…
            </h1>
          </>
        ) : null}

        {state === 'failed' ? (
          <>
            <p className="eyebrow">飞书登录失败</p>
            <h1
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: '-0.02em',
                color: 'var(--color-ink)',
              }}
            >
              无法完成登录
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
                onClick={() => navigate('/login', { replace: true })}
                type="button"
              >
                返回登录
              </button>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
