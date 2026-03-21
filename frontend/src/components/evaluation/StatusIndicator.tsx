const STATUS_LABELS: Record<string, string> = {
  collecting: '收集中',
  submitted: '已提交',
  parsing: '解析中',
  evaluated: '已评估',
  reviewing: '复核中',
  calibrated: '已校准',
  approved: '已审批',
  published: '已发布',
  active: '启用',
  inactive: '停用',
  pending: '待处理',
  completed: '已完成',
  failed: '失败',
  queued: '排队中',
  processing: '处理中',
  rejected: '已驳回',
  parsed: '已解析',
};

const STATUS_STYLES: Record<string, string> = {
  collecting: 'bg-slate-100 text-slate-700',
  submitted: 'bg-sky-100 text-sky-700',
  parsing: 'bg-amber-100 text-amber-700',
  evaluated: 'bg-emerald-100 text-emerald-700',
  reviewing: 'bg-orange-100 text-orange-700',
  calibrated: 'bg-indigo-100 text-indigo-700',
  approved: 'bg-teal-100 text-teal-700',
  published: 'bg-violet-100 text-violet-700',
  active: 'bg-emerald-100 text-emerald-700',
  inactive: 'bg-slate-200 text-slate-700',
  pending: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
  queued: 'bg-slate-100 text-slate-700',
  processing: 'bg-amber-100 text-amber-700',
  rejected: 'bg-rose-100 text-rose-700',
  parsed: 'bg-emerald-100 text-emerald-700',
};

interface StatusIndicatorProps {
  status: string;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const normalized = status.toLowerCase();
  const label = STATUS_LABELS[normalized] ?? status;
  const style = STATUS_STYLES[normalized] ?? 'bg-slate-100 text-slate-700';

  return <span className={`status-pill ${style}`}>{label}</span>;
}
