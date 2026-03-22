import type { ReactNode } from 'react';
import { Component } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ borderRadius: 8, background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger-border)', padding: '20px 24px', color: 'var(--color-danger)' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>页面加载出错。</h2>
          <p style={{ marginTop: 6, fontSize: 13 }}>请刷新页面重试，或联系管理员。</p>
        </div>
      );
    }

    return this.props.children;
  }
}