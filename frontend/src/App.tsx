import { Link, Route, Routes } from 'react-router-dom';

import { ErrorBoundary } from './components/ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ApprovalsPage } from './pages/Approvals';
import { CreateCyclePage } from './pages/CreateCycle';
import { DashboardPage } from './pages/Dashboard';
import { EmployeesPage } from './pages/Employees';
import { EvaluationDetailPage } from './pages/EvaluationDetail';
import { ImportCenterPage } from './pages/ImportCenter';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { SalarySimulatorPage } from './pages/SalarySimulator';

function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#f7e7c1_0%,#f5f0e6_30%,#efe7d8_65%,#f7f2ea_100%)] px-6 py-8 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[28px] border border-ink/10 bg-white/80 px-6 py-5 shadow-panel backdrop-blur">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-ember">Wage Adjust Platform</p>
            <h1 className="mt-2 text-2xl font-bold">AI evaluation and compensation operations hub</h1>
          </div>
          <nav className="flex flex-wrap gap-3 text-sm font-semibold">
            <a className="rounded-full px-4 py-2 text-ink/70 transition hover:bg-ink/5 hover:text-ink" href="#capabilities">
              Capabilities
            </a>
            <a className="rounded-full px-4 py-2 text-ink/70 transition hover:bg-ink/5 hover:text-ink" href="#workflow">
              Workflow
            </a>
            <a className="rounded-full px-4 py-2 text-ink/70 transition hover:bg-ink/5 hover:text-ink" href="#modules">
              Modules
            </a>
            <Link className="rounded-full bg-ink px-4 py-2 text-white" to={isAuthenticated ? '/workspace' : '/login'}>
              {isAuthenticated ? 'Open workspace' : 'Sign in'}
            </Link>
          </nav>
        </header>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <article className="rounded-[36px] bg-[#14213d] p-8 text-white shadow-panel">
            <p className="text-sm uppercase tracking-[0.28em] text-white/60">Overview</p>
            <h2 className="mt-4 max-w-3xl text-5xl font-bold leading-tight">
              One place to collect evidence, calibrate AI capability, and ship compensation decisions.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-white/75">
              The platform now covers employee submissions, cycle setup, evidence parsing, AI evaluation, salary simulation,
              approvals, imports, dashboards, and external read APIs.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-ink" to={isAuthenticated ? '/workspace' : '/register'}>
                {isAuthenticated ? 'Go to workspace' : 'Create account'}
              </Link>
              <Link className="rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-white" to="/dashboard">
                Preview dashboards
              </Link>
            </div>
          </article>

          <article className="rounded-[36px] bg-white p-6 shadow-panel">
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Delivery Status</p>
            <div className="mt-5 grid gap-4">
              {[
                ['Backend domain flows', 'Employees, cycles, files, evaluations, salary, approvals, dashboard, imports, and public APIs are live.'],
                ['Frontend workbench', 'Employees, detail review, salary simulator, approvals, dashboard, and import center are routable.'],
                ['AI upgrade path', 'DeepSeek integration is wrapped with retry, fallback, and prompt templates for safe rollout.'],
              ].map(([title, description]) => (
                <div key={title} className="rounded-[24px] bg-slate-50 p-4">
                  <h3 className="text-lg font-semibold text-ink">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" id="capabilities">
          {[
            ['Evidence Pipeline', 'Upload PPT, PDF, images, code, and docs. Parse output is normalized into structured evidence.'],
            ['AI Rating', 'Five weighted dimensions map evidence into explainable AI capability levels.'],
            ['Compensation Logic', 'Salary rules combine level bands, certifications, job context, and budget guardrails.'],
            ['Org Operations', 'Approvals, dashboards, imports, and external APIs close the loop for HR and leadership.'],
          ].map(([title, description]) => (
            <article key={title} className="rounded-[28px] bg-white p-5 shadow-panel">
              <p className="text-sm uppercase tracking-[0.22em] text-ember">{title}</p>
              <p className="mt-4 text-sm leading-6 text-slate-600">{description}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]" id="workflow">
          <article className="rounded-[32px] bg-white p-6 shadow-panel">
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Workflow</p>
            <h3 className="mt-3 text-3xl font-bold text-ink">From submission to approved salary</h3>
            <div className="mt-6 grid gap-3">
              {[
                'Create cycle and collect employee materials.',
                'Parse files into structured evidence and confidence metadata.',
                'Generate AI evaluation with five dimensions and explainable rationale.',
                'Run salary recommendation and budget simulation.',
                'Route recommendations through review, calibration, and approval.',
              ].map((step, index) => (
                <div key={step} className="flex gap-4 rounded-[22px] bg-slate-50 p-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  <p className="text-sm leading-6 text-slate-700">{step}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[32px] bg-[#f7efe3] p-6 shadow-panel" id="modules">
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Module Map</p>
            <h3 className="mt-3 text-3xl font-bold text-ink">Entry points already available in the app</h3>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {[
                ['Employees', '/employees'],
                ['Create Cycle', '/cycles/create'],
                ['Salary Simulator', '/salary-simulator'],
                ['Approvals', '/approvals'],
                ['Dashboard', '/dashboard'],
                ['Import Center', '/import-center'],
              ].map(([title, href]) => (
                <Link
                  key={title}
                  className="rounded-[22px] border border-ink/10 bg-white px-5 py-4 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:shadow-panel"
                  to={href}
                >
                  {title}
                </Link>
              ))}
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}

function WorkspacePage() {
  const { logout, user } = useAuth();

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,#14213d_0%,#1f3a5f_55%,#d97706_140%)] px-6 py-10 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[28px] border border-white/10 bg-white/10 p-6 backdrop-blur">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-white/60">Workspace Overview</p>
            <h1 className="mt-2 text-3xl font-bold">Welcome, {user?.email}</h1>
            <p className="mt-2 text-sm text-white/70">Current role: {user?.role}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-white" to="/">
              Product home
            </Link>
            <button className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-ink" onClick={logout} type="button">
              Sign out
            </button>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <article className="rounded-[28px] border border-white/10 bg-white/10 p-6 backdrop-blur">
            <p className="text-sm uppercase tracking-[0.24em] text-white/60">Mission Control</p>
            <h2 className="mt-3 text-3xl font-bold">Run the full review cycle from one overview page</h2>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/75">
              Use this workspace as the navigation layer for evaluation operations. Every major module below is already
              connected to the current backend services or prepared for direct API integration.
            </p>
          </article>
          <article className="rounded-[28px] border border-white/10 bg-white/10 p-6 backdrop-blur">
            <p className="text-sm uppercase tracking-[0.24em] text-white/60">Current Footprint</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {[
                ['9', 'Core domains'],
                ['39', 'Backend tests passing'],
                ['6', 'Primary workbench modules'],
              ].map(([value, label]) => (
                <div key={label} className="rounded-[22px] bg-white/10 p-4">
                  <p className="text-3xl font-bold">{value}</p>
                  <p className="mt-2 text-sm text-white/70">{label}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {[
            ['Employees', 'Browse employee records and evaluation entry points.', '/employees'],
            ['Create Cycle', 'Create a new evaluation cycle and budget plan.', '/cycles/create'],
            ['Simulator', 'Model salary budget scenarios and recommendation totals.', '/salary-simulator'],
            ['Approvals', 'Review pending salary decisions and approval status.', '/approvals'],
            ['Dashboard', 'Inspect organization insights, heatmaps, and ROI distribution.', '/dashboard'],
            ['Import Center', 'Track bulk import jobs and template downloads.', '/import-center'],
          ].map(([title, description, href]) => (
            <Link key={title} className="rounded-[28px] border border-white/10 bg-white/10 p-6 backdrop-blur transition hover:bg-white/15" to={href}>
              <h2 className="text-xl font-semibold">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-white/75">{description}</p>
            </Link>
          ))}
        </section>
      </div>
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<LoginPage />} path="/login" />
          <Route element={<RegisterPage />} path="/register" />
          <Route element={<ProtectedRoute />}>
            <Route element={<WorkspacePage />} path="/workspace" />
            <Route element={<EmployeesPage />} path="/employees" />
            <Route element={<EvaluationDetailPage />} path="/employees/:employeeId" />
            <Route element={<CreateCyclePage />} path="/cycles/create" />
            <Route element={<SalarySimulatorPage />} path="/salary-simulator" />
            <Route element={<ApprovalsPage />} path="/approvals" />
            <Route element={<DashboardPage />} path="/dashboard" />
            <Route element={<ImportCenterPage />} path="/import-center" />
          </Route>
        </Routes>
      </ErrorBoundary>
    </AuthProvider>
  );
}
