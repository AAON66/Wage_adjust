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
    <aside className="app-sidebar animate-fade-up">
      <div className="border-b border-[#e6eef9] pb-4">
        <p className="eyebrow">智评调薪</p>
        <h1 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-ink">智评调薪平台</h1>
        <p className="mt-2 text-sm leading-6 text-steel">{getRoleLabel(user?.role)}工作区</p>
      </div>

      <nav className="mt-5 flex flex-1 flex-col gap-1">
        <NavLink className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`} to={homePath}>
          <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-ember/80" />
          <div>
            <div className="font-medium">角色首页</div>
            <div className="mt-1 text-xs text-steel">返回当前身份的主工作台</div>
          </div>
        </NavLink>
        {modules.map((module) => (
          <NavLink className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`} key={module.href} to={module.href}>
            <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-[#bfd1ff]" />
            <div>
              <div className="font-medium">{module.title}</div>
              <div className="mt-1 text-xs text-steel">{module.description}</div>
            </div>
          </NavLink>
        ))}
      </nav>

      <div className="space-y-3 border-t border-[#e6eef9] pt-4">
        <div className="rounded-[22px] bg-[#f6f9ff] px-4 py-3">
          <p className="text-xs uppercase tracking-[0.18em] text-[#6e8dd8]">当前账号</p>
          <p className="mt-2 text-sm font-medium text-ink">{user?.email}</p>
        </div>
        <div className="flex gap-2">
          <Link className="chip-button flex-1 text-center" to="/">
            首页
          </Link>
          <button className="chip-button flex-1" onClick={logout} type="button">
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
          <header className="surface animate-fade-up px-6 py-6 lg:px-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="eyebrow">{getRoleLabel(user?.role)}工作区</p>
                <h1 className="page-title">{title}</h1>
                <p className="page-desc">{description}</p>
              </div>
              {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
            </div>
          </header>
          <div className="mt-5 space-y-5">{children}</div>
        </div>
      </div>
    </main>
  );
}
