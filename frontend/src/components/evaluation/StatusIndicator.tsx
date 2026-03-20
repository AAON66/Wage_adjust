const STATUS_LABELS: Record<string, string> = {
  collecting: 'Collecting',
  submitted: 'Submitted',
  parsing: 'Parsing',
  evaluated: 'Evaluated',
  reviewing: 'Reviewing',
  calibrated: 'Calibrated',
  approved: 'Approved',
  published: 'Published',
  active: 'Active',
  inactive: 'Inactive',
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
};

interface StatusIndicatorProps {
  status: string;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const normalized = status.toLowerCase();
  const label = STATUS_LABELS[normalized] ?? status;
  const style = STATUS_STYLES[normalized] ?? 'bg-slate-100 text-slate-700';

  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${style}`}>{label}</span>;
}