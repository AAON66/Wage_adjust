import { Link } from 'react-router-dom';

interface TalentSpotlightItem {
  employee_id: string;
  employee_name: string;
  department: string;
  ai_level: string;
  overall_score: number;
  recommendation_status: string | null;
  final_adjustment_ratio: number | null;
}

interface TalentSpotlightPanelProps {
  items: TalentSpotlightItem[];
}

function formatPercent(value: number | null): string {
  if (value == null) {
    return '--';
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function TalentSpotlightPanel({ items }: TalentSpotlightPanelProps) {
  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">人才聚焦</p>
          <h3 className="section-title">本期重点关注名单</h3>
          <p className="section-note">按综合评分排序，优先帮助你看到值得保留、晋升或重点沟通的员工。</p>
        </div>
        <p className="dashboard-summary-inline">Top {items.length}</p>
      </div>
      <div className="dashboard-talent-list">
        {items.map((item, index) => (
          <article className="dashboard-talent-item" key={item.employee_id}>
            <div className="dashboard-talent-head">
              <div>
                <p className="dashboard-rank-tag">TOP {index + 1}</p>
                <h4 className="dashboard-talent-name">{item.employee_name}</h4>
                <p className="dashboard-talent-meta">{item.department}</p>
              </div>
              <div className="dashboard-talent-score">
                <span>{item.ai_level}</span>
                <strong>{item.overall_score.toFixed(1)}</strong>
              </div>
            </div>
            <div className="dashboard-talent-stats">
              <span>建议状态：{item.recommendation_status ?? '未生成建议'}</span>
              <span>建议涨幅：{formatPercent(item.final_adjustment_ratio)}</span>
            </div>
            <Link className="chip-button" style={{ justifyContent: 'center' }} to={`/employees/${item.employee_id}`}>
              查看员工详情
            </Link>
          </article>
        ))}
        {!items.length ? <p className="text-sm text-steel">当前周期还没有可展示的重点人才数据。</p> : null}
      </div>
    </section>
  );
}
