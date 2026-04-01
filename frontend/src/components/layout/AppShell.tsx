import { useState, type ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';

import { useAuth } from '../../hooks/useAuth';
import { getRoleHomePath, getRoleLabel, getRoleModules, getSettingsModule } from '../../utils/roleAccess';
import { NAV_ICONS, IconHome } from '../icons/NavIcons';

interface AppShellProps {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}

function ShellSidebar() {
  const { user, logout } = useAuth();
  const groups = getRoleModules(user?.role);
  const settingsModule = getSettingsModule();
  const homePath = getRoleHomePath(user?.role);

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    const saved: Record<string, boolean> = {};
    groups.forEach(g => {
      if (g.collapsible) {
        const key = `nav_collapsed_${g.id}`;
        const val = localStorage.getItem(key);
        saved[g.id] = val === 'true';
      }
    });
    return saved;
  });

  function toggleGroup(groupId: string) {
    setCollapsed(prev => {
      const next = { ...prev, [groupId]: !prev[groupId] };
      localStorage.setItem(`nav_collapsed_${groupId}`, String(next[groupId]));
      return next;
    });
  }

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
        <NavLink className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`} to={homePath} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <IconHome /> 角色首页
        </NavLink>

        {groups.map(group => {
          if (group.items.length === 0) return null;

          if (!group.collapsible) {
            return group.items.map(item => {
              const IconFn = NAV_ICONS[item.icon];
              return (
                <NavLink
                  className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
                  key={item.href}
                  title={item.description}
                  to={item.href}
                  style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  {IconFn ? <IconFn /> : null} {item.title}
                </NavLink>
              );
            });
          }

          const isCollapsed = collapsed[group.id] ?? false;

          return (
            <div key={group.id}>
              <button
                onClick={() => toggleGroup(group.id)}
                type="button"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '8px 16px 4px',
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--color-placeholder)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase' as const,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <span>{isCollapsed ? '▶' : '▼'} {group.label}</span>
                {isCollapsed && (
                  <span style={{ fontSize: 10, fontWeight: 500 }}>({group.items.length})</span>
                )}
              </button>
              {!isCollapsed && group.items.map(item => {
                const IconFn = NAV_ICONS[item.icon];
                return (
                  <NavLink
                    className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
                    key={item.href}
                    title={item.description}
                    to={item.href}
                    style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                  >
                    {IconFn ? <IconFn /> : null} {item.title}
                  </NavLink>
                );
              })}
            </div>
          );
        })}

        <NavLink
          className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
          to={settingsModule.href}
          title={settingsModule.description}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          {NAV_ICONS[settingsModule.icon] ? NAV_ICONS[settingsModule.icon]() : null} {settingsModule.title}
        </NavLink>
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
          {user && !user.employee_id && user.role !== 'admin' ? (
            <div style={{
              background: '#FFF3CD',
              borderBottom: '1px solid #FFD8A8',
              padding: '10px 20px',
              fontSize: 13,
              color: '#856404',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span>您尚未绑定员工信息，部分功能受限。</span>
              <Link to="/settings" style={{ color: '#856404', fontWeight: 600, textDecoration: 'underline' }}>立即绑定</Link>
            </div>
          ) : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>{children}</div>
        </div>
      </div>
    </main>
  );
}
