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
      {/* Logo / Brand */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '0.04em' }}>
          智评调薪
        </div>
        <div style={{ fontSize: 13, color: 'var(--color-steel)', marginTop: 4 }}>
          {getRoleLabel(user?.role)}工作区
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '8px 0', overflowY: 'auto' }}>
        <NavLink
          className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
          to={homePath}
        >
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

      {/* User profile */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--color-border)' }}>
        <div style={{
          fontSize: 12,
          color: 'var(--color-steel)',
          marginBottom: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {user?.email}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link
            className="chip-button"
            style={{ flex: 1, justifyContent: 'center' }}
            to="/"
          >
            首页
          </Link>
          <button
            className="chip-button"
            style={{ flex: 1, justifyContent: 'center' }}
            onClick={logout}
            type="button"
          >
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
          <header className="surface" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
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
