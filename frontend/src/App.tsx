import axios from "axios";
import { Link, Navigate, Route, Routes, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { ApprovalsPage } from "./pages/Approvals";
import { AttendanceManagementPage } from "./pages/AttendanceManagement";
import { ApiDocsPage } from "./pages/ApiDocs";
import { CreateCyclePage } from "./pages/CreateCycle";
import { DashboardPage } from "./pages/Dashboard";
import { EmployeesPage } from "./pages/Employees";
import { EmployeeAdminPage } from "./pages/EmployeeAdmin";
import { EligibilityManagementPage } from "./pages/EligibilityManagementPage";
import { EvaluationDetailPage } from "./pages/EvaluationDetail";
import { FeishuConfigPage } from "./pages/FeishuConfig";
import { ImportCenterPage } from "./pages/ImportCenter";
import { LoginPage } from "./pages/Login";
import { MyReviewPage } from "./pages/MyReview";
import { SalarySimulatorPage } from "./pages/SalarySimulator";
import { SettingsPage } from "./pages/Settings";
import { ApiKeyManagementPage } from "./pages/ApiKeyManagement";
import { AuditLogPage } from "./pages/AuditLog";
import { UserAdminPage } from "./pages/UserAdmin";
import { WebhookManagementPage } from "./pages/WebhookManagement";
import { fetchEmployees } from "./services/employeeService";
import type { EmployeeRecord } from "./types/api";
import { findEmployeeForUser } from "./utils/employeeIdentity";
import { getRoleHomePath, getRoleLabel, getRoleModules, flattenMenuGroups } from "./utils/roleAccess";

const homeHighlights = [
  ["信息更少", "先看到关键入口，需要时再展开细节。"],
  ["分工更清晰", "按角色收敛界面，减少无关操作干扰。"],
  ["操作更直接", "登录后回到对应工作区，不绕路。"],
];

const publicModuleLinks = [
  ["员工评估", "员工列表、详情与评估状态。", "/employees"],
  ["创建周期", "配置评估周期与预算。", "/cycles/create"],
  ["调薪模拟", "按预算与范围查看建议方案。", "/salary-simulator"],
  ["审批中心", "处理待审批调薪建议。", "/approvals"],
  ["组织看板", "查看组织分布与 ROI。", "/dashboard"],
  ["导入中心", "模板下载、批量导入与结果追踪。", "/import-center"],
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      "正在校验员工权限时发生错误。";
  }
  return "正在校验员工权限时发生错误。";
}

function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const journeySteps = [
    ["01", "收集材料", "统一承接员工材料与上传结果。"],
    ["02", "完成评估", "AI 结果与人工复核放在同一流程里。"],
    ["03", "推进调薪", "预算测算、审批与发布继续衔接。"],
  ];
  const roleDetails = [
    {
      key: "admin",
      title: "管理员",
      summary: "全链路配置、预算、导入、账号与监管。",
      detail: "聚焦周期配置、预算、账号与流程治理，首页不再提前铺开完整后台结构。",
      href: "/workspace",
      action: "进入管理员工作区",
    },
    {
      key: "hrbp",
      title: "HRBP",
      summary: "评估协同、审批推进、组织观察。",
      detail: "重点查看复核质量、审批推进状态与组织洞察，不需要被全局配置打扰。",
      href: "/workspace",
      action: "进入 HRBP 工作区",
    },
    {
      key: "manager",
      title: "主管",
      summary: "团队评估处理与审批任务。",
      detail: "优先看到团队相关待办，减少跨角色信息堆叠，让入口更直接。",
      href: "/workspace",
      action: "进入主管工作区",
    },
    {
      key: "employee",
      title: "员工",
      summary: "个人评估进展、材料状态与密码设置。",
      detail: "员工侧保持轻量，只保留与个人评估和账号安全直接相关的信息。",
      href: "/login",
      action: "登录员工入口",
    },
  ];
  const moduleDetails = publicModuleLinks.map(([title, summary, href]) => ({
    key: title,
    title,
    summary,
    detail: summary + " 首页默认收起，只有点击后才展开具体入口。",
    href,
    action: "打开" + title,
  }));
  const [detailMode, setDetailMode] = useState<"roles" | "modules">("roles");
  const [expandedKey, setExpandedKey] = useState<string>(roleDetails[0].key);
  const activeItems = detailMode === "roles" ? roleDetails : moduleDetails;
  const expandedItem = activeItems.find((item) => item.key === expandedKey) ?? activeItems[0];

  function switchMode(nextMode: "roles" | "modules") {
    const nextItems = nextMode === "roles" ? roleDetails : moduleDetails;
    setDetailMode(nextMode);
    setExpandedKey(nextItems[0].key);
  }

  function revealDetails(nextMode: "roles" | "modules") {
    switchMode(nextMode);
    document.getElementById("home-details")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <main className="app-shell px-4 py-4 text-ink lg:px-5">
      <div className="mx-auto flex min-h-screen max-w-[1380px] flex-col gap-5">
        <header className="flex animate-fade-up flex-wrap items-center justify-between gap-3 px-1 pt-2">
          <div>
            <p className="eyebrow">智评调薪平台</p>
            <p className="mt-2 text-sm text-steel">企业内部评估与调薪运营入口</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="action-secondary" to="/login">账号登录</Link>
            <Link className="action-primary" to={isAuthenticated ? getRoleHomePath(user?.role) : "/login"}>
              {isAuthenticated ? "进入工作区" : "进入系统"}
            </Link>
          </div>
        </header>

        <section className="surface animate-fade-up px-6 py-7 lg:px-8 lg:py-8" style={{ animationDelay: "60ms" }}>
          <div className="grid gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
            <div>
              <span style={{ display: 'inline-flex', borderRadius: 4, border: '1px solid var(--color-border)', background: 'var(--color-primary-light)', padding: '3px 10px', fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-primary)' }}>
                更简洁的首页入口
              </span>
              <h1 className="mt-5 max-w-3xl text-[38px] font-semibold leading-[1.02] tracking-[-0.06em] text-ink lg:text-[48px]">
                企业内部评估与调薪平台
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-7 text-steel lg:text-[15px]">
                首页先展示系统入口、流程概览和角色说明。更详细的模块说明与入口，交给按钮按需展开，不再一上来堆满整屏信息。
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link className="action-primary" to={isAuthenticated ? getRoleHomePath(user?.role) : "/login"}>
                  {isAuthenticated ? "继续进入工作区" : "立即登录"}
                </Link>
                <button className="action-secondary" onClick={() => revealDetails("roles")} type="button">
                  查看角色说明
                </button>
              </div>
              <p className="mt-4 text-sm text-steel">账号由管理员统一开通，登录后会自动回到对应角色工作区。</p>
            </div>

            <div className="surface-subtle p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="eyebrow">流程概览</p>
                  <h2 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-ink">三步完成闭环</h2>
                </div>
                <span style={{ borderRadius: 4, background: 'var(--color-primary-light)', padding: '3px 10px', fontSize: 12, fontWeight: 500, color: 'var(--color-primary)' }}>核心信息</span>
              </div>
              <div className="mt-5 space-y-3">
                {journeySteps.map(([step, title, description]) => (
                  <div className="surface flex items-start gap-4 px-4 py-4" key={step}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, flexShrink: 0, borderRadius: 8, background: 'var(--color-primary-light)', fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>
                      {step}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink">{title}</p>
                      <p className="mt-1 text-sm leading-6 text-steel">{description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          {homeHighlights.map(([title, description], index) => (
            <article className="surface animate-fade-up px-5 py-5" key={title} style={{ animationDelay: String(180 + index * 60) + "ms" }}>
              <h3 className="text-base font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-steel">{description}</p>
            </article>
          ))}
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" id="home-details" style={{ animationDelay: "320ms" }}>
          <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4" style={{ borderColor: 'var(--color-border)' }}>
            <div>
              <p className="eyebrow">交互式详情</p>
              <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">点开后再看详细说明</h3>
              <p className="mt-2 text-sm leading-6 text-steel">把角色说明和功能入口收在一处，用户主动点击时再展开。</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className={"chip-button" + (detailMode === "roles" ? " chip-button-active" : "")}
                onClick={() => switchMode("roles")}
                type="button"
              >
                角色说明
              </button>
              <button
                className={"chip-button" + (detailMode === "modules" ? " chip-button-active" : "")}
                onClick={() => switchMode("modules")}
                type="button"
              >
                模块入口
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="space-y-3">
              {activeItems.map((item) => {
                const isExpanded = item.key === expandedItem.key;
                return (
                  <article
                    className="border px-4 py-4 transition duration-200"
                    style={{
                      borderRadius: 8,
                      borderColor: isExpanded ? 'var(--color-primary-border)' : 'var(--color-border)',
                      background: isExpanded ? 'var(--color-primary-light)' : 'var(--color-bg-surface)',
                    }}
                    key={item.key}
                  >
                    <button
                      aria-expanded={isExpanded}
                      className="flex w-full items-start justify-between gap-4 text-left"
                      onClick={() => setExpandedKey(item.key)}
                      type="button"
                    >
                      <div>
                        <h4 className="text-base font-semibold text-ink">{item.title}</h4>
                        <p className="mt-1 text-sm leading-6 text-steel">{item.summary}</p>
                      </div>
                      <span style={{ marginTop: 4, fontSize: 12, fontWeight: 600, color: 'var(--color-primary)', transition: 'transform 0.2s', display: 'inline-block', transform: isExpanded ? 'rotate(45deg)' : 'none' }}>+</span>
                    </button>
                    {isExpanded ? (
                      <div className="mt-4 border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
                        <p className="text-sm leading-7 text-steel">{item.detail}</p>
                        <Link className="mt-4 inline-flex text-sm font-medium" style={{ color: 'var(--color-primary)' }} to={item.href}>
                          {item.action}
                        </Link>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>

            <aside className="surface-subtle min-h-[280px] px-5 py-5 lg:px-6">
              <p className="eyebrow">当前详情</p>
              <h4 className="mt-3 text-[30px] font-semibold leading-[1.08] tracking-[-0.05em] text-ink">{expandedItem.title}</h4>
              <p className="mt-4 text-sm leading-7 text-steel">{expandedItem.detail}</p>
              <div className="mt-6 surface px-4 py-4">
                <p className="eyebrow">摘要</p>
                <p className="mt-3 text-sm leading-7 text-steel">{expandedItem.summary}</p>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link className="action-primary" to={expandedItem.href}>
                  {expandedItem.action}
                </Link>
                <Link className="action-secondary" to={isAuthenticated ? getRoleHomePath(user?.role) : "/login"}>
                  {isAuthenticated ? "返回工作区" : "先去登录"}
                </Link>
              </div>
            </aside>
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: "380ms" }}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="eyebrow">开发者支持</p>
              <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">API 文档</h3>
              <p className="mt-2 text-sm leading-6 text-steel">按模块查看接口路径、鉴权方式和请求说明。</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link className="action-secondary" to="/login">进入系统</Link>
              <Link className="action-primary" to="/api-docs">查看 API 文档</Link>
            </div>
          </div>
        </section>

      </div>
    </main>
  );
}

function WorkspacePage() {
  const { user } = useAuth();
  const menuGroups = getRoleModules(user?.role);
  const modules = flattenMenuGroups(menuGroups);
  const roleSummary = {
    admin: ["全局运营", "重点关注周期配置、预算、账号、导入与流程治理。"],
    hrbp: ["协同运营", "重点关注复核质量、审批推进与组织状态。"],
    manager: ["团队管理", "重点关注团队成员评估与审批动作。"],
  }[user?.role ?? ""] ?? ["工作区", "根据当前角色展示可访问功能。"];

  return (
    <AppShell
      title={getRoleLabel(user?.role) + "工作台"}
      description="查看当前角色可用模块。"
      actions={<span style={{ borderRadius: 4, background: 'var(--color-primary-light)', padding: '4px 12px', fontSize: 13, color: 'var(--color-primary)' }}>当前身份：{getRoleLabel(user?.role)}</span>}
    >
      <section className="metric-strip animate-fade-up">
        {[
          [getRoleLabel(user?.role), "当前角色", "你看到的是对应职责下的专属工作区。"],
          [String(modules.length), "可访问模块", "只展示当前角色可实际使用的页面。"],
          [roleSummary[0], "工作重点", roleSummary[1]],
        ].map(([value, label, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface animate-fade-up px-6 py-6 lg:px-7">
        <div className="flex items-end justify-between gap-3 border-b pb-4" style={{ borderColor: 'var(--color-border)' }}>
          <div>
            <p className="eyebrow">功能入口</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">角色可用功能</h2>
          </div>
          <p className="text-sm text-steel">按职责划分，不展示无关模块</p>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => (
            <Link className="list-row group" key={module.title} title={module.description} to={module.href}>
              <h3 className="text-lg font-semibold text-ink">{module.title}</h3>
              <p className="list-row-note">{module.description}</p>
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
  const [isLoading, setIsLoading] = useState(user?.role === "employee");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEmployees() {
      if (user?.role !== "employee") {
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

  if (user?.role !== "employee") {
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
        <div className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</div>
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
          <Route element={<ApiDocsPage />} path="/api-docs" />
          <Route element={<LoginPage />} path="/login" />
          <Route element={<Navigate replace to="/login" />} path="/register" />

          <Route element={<ProtectedRoute allowedRoles={["admin", "hrbp", "manager"]} />}>
            <Route element={<WorkspacePage />} path="/workspace" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["employee"]} />}>
            <Route element={<MyReviewPage />} path="/my-review" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["admin", "hrbp", "manager"]} />}>
            <Route element={<EmployeesPage />} path="/employees" />
            <Route element={<EligibilityManagementPage />} path="/eligibility" />
            <Route element={<ApprovalsPage />} path="/approvals" />
            <Route element={<DashboardPage />} path="/dashboard" />
            <Route element={<UserAdminPage />} path="/user-admin" />
            <Route element={<EmployeeAdminPage />} path="/employee-admin" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["admin", "hrbp", "manager", "employee"]} />}>
            <Route element={<EmployeeScopedEvaluationPage />} path="/employees/:employeeId" />
            <Route element={<SettingsPage />} path="/settings" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
            <Route element={<CreateCyclePage />} path="/cycles/create" />
            <Route element={<AuditLogPage />} path="/audit-log" />
            <Route element={<ApiKeyManagementPage />} path="/api-key-management" />
            <Route element={<WebhookManagementPage />} path="/webhook-management" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["admin", "hrbp"]} />}>
            <Route element={<SalarySimulatorPage />} path="/salary-simulator" />
            <Route element={<ImportCenterPage />} path="/import-center" />
            <Route element={<AttendanceManagementPage />} path="/attendance" />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
            <Route element={<FeishuConfigPage />} path="/feishu-config" />
          </Route>
        </Routes>
      </ErrorBoundary>
    </AuthProvider>
  );
}
