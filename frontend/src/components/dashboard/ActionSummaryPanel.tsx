interface ActionSummaryItem {
  title: string;
  value: string;
  note: string;
  severity: string;
}

interface CycleSummary {
  cycle_name: string;
  review_period: string;
  status: string;
  budget_amount: string;
}

interface ActionSummaryPanelProps {
  cycleSummary: CycleSummary | null;
  items: ActionSummaryItem[];
}

function severityLabel(severity: string): string {
  if (severity === 'high') {
    return '高优先级';
  }
  if (severity === 'medium') {
    return '需要跟进';
  }
  return '状态稳定';
}

function severityClass(severity: string): string {
  if (severity === 'high') {
    return 'dashboard-priority-high';
  }
  if (severity === 'medium') {
    return 'dashboard-priority-medium';
  }
  return 'dashboard-priority-low';
}

export function ActionSummaryPanel({ cycleSummary, items }: ActionSummaryPanelProps) {
  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">关键动作</p>
          <h3 className="section-title">本期需要优先处理的事项</h3>
          <p className="section-note">把复核、审批和预算风险集中放在一个工作面里，减少在不同页面之间跳转查找。</p>
        </div>
        {cycleSummary ? (
          <div className="dashboard-summary-inline" style={{ flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            <span style={{ fontWeight: 600, color: 'var(--color-ink)', fontSize: 12 }}>{cycleSummary.cycle_name}</span>
            <span>{cycleSummary.review_period}</span>
          </div>
        ) : null}
      </div>
      <div className="dashboard-priority-list">
        {items.map((item) => (
          <article className="dashboard-priority-item" key={item.title}>
            <div className="dashboard-priority-topline">
              <div>
                <p className="dashboard-priority-title">{item.title}</p>
                <p className="dashboard-priority-value">{item.value}</p>
              </div>
              <span className={`dashboard-priority-pill ${severityClass(item.severity)}`}>{severityLabel(item.severity)}</span>
            </div>
            <p className="dashboard-priority-note">{item.note}</p>
          </article>
        ))}
        {!items.length ? <p className="text-sm text-steel">当前没有需要优先处理的动作。</p> : null}
      </div>
    </section>
  );
}
