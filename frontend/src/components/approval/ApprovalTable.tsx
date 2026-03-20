interface ApprovalRow {
  id: string;
  employeeName: string;
  department: string;
  aiLevel: string;
  recommendedIncrease: string;
  status: 'pending' | 'approved' | 'rejected';
  approver: string;
}

interface ApprovalTableProps {
  rows: ApprovalRow[];
}

const STATUS_STYLES: Record<ApprovalRow['status'], string> = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-rose-100 text-rose-700',
};

export function ApprovalTable({ rows }: ApprovalTableProps) {
  return (
    <section className="rounded-[32px] bg-white p-6 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Approval Center</p>
          <h2 className="mt-2 text-3xl font-bold text-ink">Pending salary approvals</h2>
        </div>
        <span className="text-sm text-slate-500">{rows.length} records</span>
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-3 text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-4">Employee</th>
              <th className="px-4">Department</th>
              <th className="px-4">AI Level</th>
              <th className="px-4">Increase</th>
              <th className="px-4">Approver</th>
              <th className="px-4">Status</th>
              <th className="px-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="bg-slate-50 text-slate-700">
                <td className="rounded-l-[20px] px-4 py-4 font-semibold text-ink">{row.employeeName}</td>
                <td className="px-4 py-4">{row.department}</td>
                <td className="px-4 py-4">{row.aiLevel}</td>
                <td className="px-4 py-4">{row.recommendedIncrease}</td>
                <td className="px-4 py-4">{row.approver}</td>
                <td className="px-4 py-4">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[row.status]}`}>{row.status}</span>
                </td>
                <td className="rounded-r-[20px] px-4 py-4">
                  <div className="flex flex-wrap gap-2">
                    <button className="rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white" type="button">
                      Approve
                    </button>
                    <button className="rounded-full border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-600" type="button">
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}