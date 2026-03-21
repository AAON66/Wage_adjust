import axios from 'axios';
import { Link, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ErrorBoundary } from './components/ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ApprovalsPage } from './pages/Approvals';
import { CreateCyclePage } from './pages/CreateCycle';
import { DashboardPage } from './pages/Dashboard';
import { EmployeesPage } from './pages/Employees';
import { EvaluationDetailPage } from './pages/EvaluationDetail';
import { ImportCenterPage } from './pages/ImportCenter';
import { LoginPage } from './pages/Login';
import { MyReviewPage } from './pages/MyReview';
import { SalarySimulatorPage } from './pages/SalarySimulator';
import { SettingsPage } from './pages/Settings';
import { UserAdminPage } from './pages/UserAdmin';
import { fetchEmployees } from './services/employeeService';
import type { EmployeeRecord } from './types/api';
import { findEmployeeForUser } from './utils/employeeIdentity';
import { getRoleHomePath, getRoleLabel, getRoleModules } from './utils/roleAccess';

const homeHighlights = [
  ['统一运营闭环', '材料、评估、预算、审批在同一条链路内流转。'],
  ['角色分工清晰', '管理员、HRBP、主管、员工进入各自职责工作区。'],
  ['面向内部协作', '信息组织围绕真实业务处理与权限边界展开。'],
];

const capabilityCards = [
  ['证据抽取', '围绕员工材料形成结构化证据与摘要。'],
  ['评估复核', '保留 AI 结果、人工判断与维度拆解。'],
  ['预算联动', '从建议涨幅到预算占用形成可操作结果。'],
  ['审批协同', '支持待办处理、历史追踪与发布承接。'],
];

const publicModuleLinks = [
  ['员工评估', '员工列表、详情与评估状态。', '/employees'],
  ['创建周期', '配置评估周期与预算。', '/cycles/create'],
  ['调薪模拟', '按预算与范围查看建议方案。', '/salary-simulator'],
  ['审批中心', '处理待审批调薪建议。', '/approvals'],
  ['组织看板', '查看组织分布与 ROI。', '/dashboard'],
  ['导入中心', '模板下载、批量导入与结果追踪。', '/import-center'],
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '正在校验员工权限时发生错误。';
  }
  return '正在校验员工权限时发生错误。';
}

function HomePage() {
  const { isAuthenticated, user } = useAuth();

  return (
    <main className="app-shell px-4 py-4 text-ink lg:px-5">
      <div className="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-5">
        <header className="surface animate-fade-up px-6 py-5 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="eyebrow">智评调薪平台</p>
              <h1 className="mt-2 text-[26px] font-semibold tracking-[-0.03em] text-ink lg:text-[34px]">企业内部评估与调薪平台</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-steel">
                面向公司内部评估与调薪运营场景，统一承接员工材料、AI 评估、预算测算、审批协同和组织洞察。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link className="chip-button" to="/login">账号登录</Link>
              <Link className="action-primary" to={isAuthenticated ? getRoleHomePath(user?.role) : '/login'}>
                {isAuthenticated ? '进入工作区' : '进入系统'}
              </Link>
            </div>
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[1.18fr_0.82fr]">
          <article className="surface animate-fade-up overflow-hidden px-6 py-8 lg:px-8" style={{ animationDelay: '60ms' }}>
            <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <div>
                <p className="eyebrow">角色化体验</p>
                <h2 className="mt-3 text-[40px] font-semibold leading-[1.06] tracking-[-0.05em] text-ink lg:text-[54px]">
                  简洁、克制、面向协作的内部运营界面
                </h2>
                <p className="mt-5 max-w-xl text-sm leading-7 text-steel">
                  设计语言参考飞书应用的产品气质：浅色雾面背景、细线分区、信息优先的内容排布，以及围绕角色职责展开的工作区结构。
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link className="action-primary" to={isAuthenticated ? getRoleHomePath(user?.role) : '/login'}>
                    {isAuthenticated ? '打开角色工作区' : '登录后进入'}
                  </Link>
                  <span className="chip-button">账号由管理员统一开通</span>
                </div>
              </div>
              <div className="surface-subtle relative overflow-hidden px-5 py-5">
                <div className="absolute right-0 top-0 h-28 w-28 rounded-full bg-[#dbe6ff] blur-3xl" />
                <div className="relative space-y-3">
                  {[
                    ['管理员', '全链路配置、预算、导入、账号与监管'],
                    ['HRBP', '评估协同、审批推进、组织看板'],
                    ['主管', '团队评估处理与审批任务'],
                    ['员工', '个人评估中心、密码设置与材料进展'],
                  ].map(([role, desc]) => (
                    <div className="rounded-[22px] border border-[#dce6f5] bg-white/78 px-4 py-4" key={role}>
                      <p className="text-sm font-medium text-ink">{role}</p>
                      <p className="mt-1 text-sm leading-6 text-steel">{desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>

          <article className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '120ms' }}>
            <p className="eyebrow">平台特性</p>
            <div className="mt-4 grid gap-3">
              {[
                ['角色分台', '不同身份进入不同工作区与导航结构。'],
                ['权限边界', '自注册入口默认关闭，账号统一由内部管理。'],
                ['账号安全', '每位用户都可以在个人设置中自行修改登录密码。'],
              ].map(([title, desc]) => (
                <div className="surface-subtle px-4 py-4" key={title}>
                  <p className="font-medium text-ink">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-steel">{desc}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {homeHighlights.map(([title, description], index) => (
            <article className="surface animate-fade-up px-5 py-5" key={title} style={{ animationDelay: `${180 + index * 60}ms` }}>
              <h3 className="text-base font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-steel">{description}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {capabilityCards.map(([title, description], index) => (
            <article className="surface animate-fade-up px-5 py-5" key={title} style={{ animationDelay: `${280 + index * 50}ms` }}>
              <p className="eyebrow">能力模块</p>
              <h3 className="mt-3 text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-steel">{description}</p>
            </article>
          ))}
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '420ms' }}>
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#e6eef9] pb-4">
            <div>
              <p className="eyebrow">功能入口</p>
              <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">核心功能入口</h3>
            </div>
            <Link className="chip-button" to={isAuthenticated ? getRoleHomePath(user?.role) : '/login'}>
              进入工作区
            </Link>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {publicModuleLinks.map(([title, description, href]) => (
              <Link className="list-row" key={title} to={href}>
                <h4 className="text-base font-semibold text-ink">{title}</h4>
                <p className="mt-2 text-sm leading-6 text-steel">{description}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function WorkspacePage() {
  const { user } = useAuth();
  const modules = getRoleModules(user?.role);
  const roleSummary = {
    admin: ['全局运营', '重点关注周期配置、预算、账号、导入与流程治理。'],
    hrbp: ['协同运营', '重点关注复核质量、审批推进与组织状态。'],
    manager: ['团队管理', '重点关注团队成员评估与审批动作。'],
  }[user?.role ?? ''] ?? ['工作区', '根据当前角色展示可访问功能。'];

  return (
    <AppShell
      title={`${getRoleLabel(user?.role)}工作台`}
      description="当前界面仅保留与你职责相关的操作能力，信息与导航都按角色职责重组。"
      actions={<span className="rounded-full bg-[#edf3ff] px-4 py-2 text-sm text-[#2750b6]">当前身份：{getRoleLabel(user?.role)}</span>}
    >
      <section className="metric-strip animate-fade-up">
        {[
          [getRoleLabel(user?.role), '当前角色', '你看到的是对应职责下的专属工作区。'],
          [String(modules.length), '可访问模块', '只展示当前角色可实际使用的页面。'],
          [roleSummary[0], '工作重点', roleSummary[1]],
        ].map(([value, label, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="flex items-end justify-between gap-3 border-b border-[#e6eef9] pb-4">
          <div>
            <p className="eyebrow">功能入口</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">角色可用功能</h2>
          </div>
          <p className="text-sm text-steel">按职责划分，不展示无关模块</p>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => (
            <Link className="list-row" key={module.title} to={module.href}>
              <h3 className="text-lg font-semibold text-ink">{module.title}</h3>
              <p className="mt-2 text-sm leading-6 text-steel">{module.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function EmployeeScopedEvaluationPage() {
  const { user } = useAuth();
  const { employeeId } = useParams<{ employeeId: string }>();
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [isLoading, setIsLoading] = useState(user?.role === 'employee');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEmployees() {
      if (user?.role !== 'employee') {
        setIsLoading(false);
        return;
      }
      try {
        const response = await fetchEmployees({ page: 1, page_size: 100 });
        if (!cancelled) {
          setEmployees(response.items);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadEmployees();
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (user?.role !== 'employee') {
    return <EvaluationDetailPage />;
  }

  if (isLoading) {
    return (
      <main className="app-shell flex min-h-screen items-center justify-center px-6 text-ink">
        <div className="surface px-5 py-4 text-sm text-steel">正在校验你的个人评估访问权限...</div>
      </main>
    );
  }

  if (errorMessage) {
    return (
      <main className="app-shell flex min-h-screen items-center justify-center px-6 text-ink">
        <div className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</div>
      </main>
    );
  }

  const matchedEmployee = findEmployeeForUser(user, employees);
  if (!matchedEmployee || employeeId !== matchedEmployee.id) {
    return <Navigate replace to="/my-review" />;
  }

  return <EvaluationDetailPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<LoginPage />} path="/login" />
          <Route element={<Navigate replace to="/login" />} path="/register" />

          <Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp', 'manager']} />}>
            <Route element={<WorkspacePage />} path="/workspace" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['employee']} />}>
            <Route element={<MyReviewPage />} path="/my-review" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp', 'manager']} />}>
            <Route element={<EmployeesPage />} path="/employees" />
            <Route element={<ApprovalsPage />} path="/approvals" />
            <Route element={<DashboardPage />} path="/dashboard" />
            <Route element={<UserAdminPage />} path="/user-admin" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp', 'manager', 'employee']} />}>
            <Route element={<EmployeeScopedEvaluationPage />} path="/employees/:employeeId" />
            <Route element={<SettingsPage />} path="/settings" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route element={<CreateCyclePage />} path="/cycles/create" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp']} />}>
            <Route element={<SalarySimulatorPage />} path="/salary-simulator" />
            <Route element={<ImportCenterPage />} path="/import-center" />
          </Route>
        </Routes>
      </ErrorBoundary>
    </AuthProvider>
  );
}
