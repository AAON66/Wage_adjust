import { Link } from 'react-router-dom';

import { ApprovalTable } from '../components/approval/ApprovalTable';

const APPROVAL_ROWS = [
  { id: 'a1', employeeName: 'Annie Zhang', department: 'Engineering', aiLevel: 'Level 4', recommendedIncrease: '+12%', status: 'pending' as const, approver: 'HRBP North' },
  { id: 'a2', employeeName: 'Leo Chen', department: 'Engineering', aiLevel: 'Level 4', recommendedIncrease: '+15%', status: 'pending' as const, approver: 'Comp Committee' },
  { id: 'a3', employeeName: 'Mia Wu', department: 'Product', aiLevel: 'Level 3', recommendedIncrease: '+9%', status: 'approved' as const, approver: 'HRBP Product' },
  { id: 'a4', employeeName: 'Chris Lin', department: 'Design', aiLevel: 'Level 2', recommendedIncrease: '+6%', status: 'rejected' as const, approver: 'Comp Committee' },
];

export function ApprovalsPage() {
  return (
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-start justify-between gap-4 rounded-[32px] bg-white p-6 shadow-panel">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Approvals</p>
            <h1 className="mt-2 text-4xl font-bold">Salary approval center</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              This page stages the future approval workflow APIs with a practical review table for pending, approved, and rejected compensation decisions.
            </p>
          </div>
          <div className="flex gap-3">
            <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/workspace">
              Back to workspace
            </Link>
            <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/salary-simulator">
              Open simulator
            </Link>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          {[
            ['Pending items', '2', 'bg-amber-50 text-amber-700'],
            ['Approved', '1', 'bg-emerald-50 text-emerald-700'],
            ['Rejected', '1', 'bg-rose-50 text-rose-700'],
          ].map(([label, value, classes]) => (
            <article key={label} className="rounded-[24px] bg-white p-5 shadow-panel">
              <p className="text-sm text-slate-500">{label}</p>
              <p className={`mt-3 inline-flex rounded-full px-4 py-2 text-2xl font-bold ${classes}`}>{value}</p>
            </article>
          ))}
        </section>

        <ApprovalTable rows={APPROVAL_ROWS} />
      </div>
    </main>
  );
}