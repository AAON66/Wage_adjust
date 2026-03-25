import { type ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';

import { useAuth } from '../../hooks/useAuth';
import { getRoleHomePath, getRoleLabel, getRoleModules } from '../../utils/roleAccess';

interface AppShellProps {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}

function ShellSidebar() {
  const { user, logout } = useAuth();
  const modules = getRoleModules(user?.role);
  const homePath = getRoleHomePath(user?.role);

  return (
    <aside className="app-sidebar">
      <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <span style={{ color: '#fff', fontSize: 13, fontWeight: 700, letterSpacing: '-0.02em' }}>智</span>
          </div>
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--color-ink)', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
              智评调薪
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--color-steel)', marginTop: 1 }}>{getRoleLabel(user?.role)}工作区</div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '6px 0 8px', overflowY: 'auto' }}>
        <div
          style={{
            padding: '8px 16px 4px',
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--color-placeholder)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          导航
        </div>
        <NavLink className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`} to={homePath}>
          角色首页
        </NavLink>
        {modules.map((module) => (
          <NavLink
            className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
            key={module.href}
            title={module.description}
            to={module.href}
          >
            {module.title}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '10px 12px 12px', borderTop: '1px solid var(--color-border)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 10px',
            background: 'var(--color-bg-subtle)',
            borderRadius: 6,
            marginBottom: 8,
          }}
        >
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: '50%',
              background: 'var(--color-primary-light)',
              color: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            {(user?.email?.[0] ?? '?').toUpperCase()}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-steel)', marginTop: 1 }}>{getRoleLabel(user?.role)}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <Link className="chip-button" style={{ flex: 1, justifyContent: 'center' }} to="/">
            首页
          </Link>
          <button className="chip-button" style={{ flex: 1, justifyContent: 'center' }} onClick={logout} type="button">
            退出
          </button>
        </div>
      </div>
    </aside>
  );
}

export function AppShell({ title, description, actions, children }: AppShellProps) {
  const { user } = useAuth();

  return (
    <main className="app-shell">
      <div className="app-shell-inner">
        <ShellSidebar />
        <div className="app-main">
          <header className="surface" style={{ padding: '14px 20px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <p className="eyebrow">{getRoleLabel(user?.role)}工作区</p>
                <h1 className="page-title">{title}</h1>
                {description ? <p className="page-desc">{description}</p> : null}
              </div>
              {actions ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>{actions}</div> : null}
            </div>
          </header>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>{children}</div>
        </div>
      </div>
    </main>
  );
}
