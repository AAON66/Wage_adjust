interface ApprovalRow {
  id: string;
  employeeName: string;
  department: string;
  aiLevel: string;
  cycleName: string;
  recommendedIncrease: string;
  approver: string;
  status: 'pending' | 'approved' | 'rejected';
  canAct: boolean;
}

interface ApprovalTableProps {
  rows: ApprovalRow[];
  processingId?: string | null;
  onApprove?: (approvalId: string) => void;
  onReject?: (approvalId: string) => void;
}

const STATUS_STYLES: Record<ApprovalRow['status'], string> = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-rose-100 text-rose-700',
};

const STATUS_LABELS: Record<ApprovalRow['status'], string> = {
  pending: '待处理',
  approved: '已通过',
  rejected: '已驳回',
};

export function ApprovalTable({ rows, processingId = null, onApprove, onReject }: ApprovalTableProps) {
  return (
    <section className="table-shell animate-fade-up">
      <div className="section-head px-6 py-5">
        <div>
          <p className="eyebrow">审批任务</p>
          <h2 className="section-title">待处理调薪审批</h2>
        </div>
        <span className="text-sm text-steel">{rows.length} 条记录</span>
      </div>

      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>员工</th>
              <th>部门</th>
              <th>评估周期</th>
              <th>AI 等级</th>
              <th>建议涨幅</th>
              <th>审批人</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isProcessing = processingId === row.id;
              return (
                <tr key={row.id}>
                  <td>
                    <div className="font-medium text-ink">{row.employeeName}</div>
                    <div className="mt-1 text-xs text-steel">{row.department}</div>
                  </td>
                  <td>{row.department}</td>
                  <td>{row.cycleName}</td>
                  <td>{row.aiLevel}</td>
                  <td className="font-medium text-ink">{row.recommendedIncrease}</td>
                  <td>{row.approver}</td>
                  <td>
                    <span className={`status-pill ${STATUS_STYLES[row.status]}`}>{STATUS_LABELS[row.status]}</span>
                  </td>
                  <td>
                    {row.canAct && onApprove && onReject ? (
                      <div className="flex flex-wrap gap-2">
                        <button className="action-primary px-4 py-2 text-xs" disabled={isProcessing} onClick={() => onApprove(row.id)} type="button">
                          {isProcessing ? '处理中...' : '通过'}
                        </button>
                        <button className="action-danger px-4 py-2 text-xs" disabled={isProcessing} onClick={() => onReject(row.id)} type="button">
                          驳回
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-steel">{row.status === 'pending' ? '等待对应审批人处理' : '已完成'}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
