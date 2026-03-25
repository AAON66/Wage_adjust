import type React from 'react';

interface ApprovalRow {
  id: string;
  employeeName: string;
  department: string;
  aiLevel: string;
  cycleName: string;
  recommendedIncrease: string;
  approver: string;
  status: 'pending' | 'approved' | 'rejected' | 'deferred';
  recommendationStatus: string;
  stepName: string;
  isCurrentStep: boolean;
  comment: string;
  deferSummary?: string;
  canAct: boolean;
}

interface ApprovalTableProps {
  rows: ApprovalRow[];
  selectedId?: string | null;
  onSelect?: (approvalId: string) => void;
}

const STATUS_STYLES: Record<ApprovalRow['status'], React.CSSProperties> = {
  pending: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  approved: { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
  rejected: { background: 'var(--color-danger-bg)', color: 'var(--color-danger)' },
  deferred: { background: 'var(--color-info-bg)', color: 'var(--color-info)' },
};

const STATUS_LABELS: Record<ApprovalRow['status'], string> = {
  pending: '待处理',
  approved: '已通过',
  rejected: '已驳回',
  deferred: '已暂缓',
};

export function ApprovalTable({ rows, selectedId = null, onSelect }: ApprovalTableProps) {
  return (
    <section className="table-shell animate-fade-up">
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          padding: '14px 16px',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div>
          <p className="eyebrow">审批任务</p>
          <h2 className="section-title">审批流转明细</h2>
        </div>
        <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>{rows.length} 条记录</span>
      </div>

      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>员工</th>
              <th>审批节点</th>
              <th>评估周期</th>
              <th>AI 等级</th>
              <th>建议涨幅</th>
              <th>审批人</th>
              <th>节点状态</th>
              <th>明细</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isSelected = selectedId === row.id;
              return (
                <tr
                  key={row.id}
                  style={{
                    background: isSelected ? 'var(--color-primary-light)' : undefined,
                  }}
                >
                  <td>
                    <div className="font-medium text-ink">{row.employeeName}</div>
                    <div className="mt-1 text-xs text-steel">{row.department}</div>
                  </td>
                  <td>
                    <div className="font-medium text-ink">{row.stepName}</div>
                    <div className="mt-1 text-xs text-steel">
                      {row.isCurrentStep ? '当前待处理节点' : row.status === 'pending' ? '等待前置节点完成' : '历史节点'}
                    </div>
                  </td>
                  <td>{row.cycleName}</td>
                  <td>{row.aiLevel}</td>
                  <td className="font-medium text-ink">{row.recommendedIncrease}</td>
                  <td>
                    <div>{row.approver}</div>
                    <div className="mt-1 text-xs text-steel">建议状态：{row.recommendationStatus}</div>
                  </td>
                  <td>
                    <span className="status-pill" style={STATUS_STYLES[row.status]}>
                      {STATUS_LABELS[row.status]}
                    </span>
                    {row.comment ? <div className="mt-2 max-w-[220px] text-xs leading-5 text-steel">{row.comment}</div> : null}
                    {row.deferSummary ? <div className="mt-2 max-w-[220px] text-xs leading-5 text-steel">{row.deferSummary}</div> : null}
                  </td>
                  <td>
                    <button className={isSelected ? 'action-primary px-4 py-2 text-xs' : 'action-secondary px-4 py-2 text-xs'} onClick={() => onSelect?.(row.id)} type="button">
                      {isSelected ? '查看中' : '查看明细'}
                    </button>
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
