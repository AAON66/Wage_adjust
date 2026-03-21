import type { EvidenceRecord } from '../../types/api';

interface EvidenceCardProps {
  evidence: EvidenceRecord;
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const confidence = `${Math.round(evidence.confidence_score * 100)}%`;

  return (
    <article className="list-row">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">{evidence.source_type}</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">{evidence.title}</h3>
        </div>
        <span className="status-pill bg-emerald-100 text-emerald-700">置信度 {confidence}</span>
      </div>
      <p className="mt-4 text-sm leading-7 text-steel">{evidence.content}</p>
      {evidence.tags?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {evidence.tags.map((tag) => (
            <span key={tag} className="chip-button px-3 py-1 text-xs">
              {tag}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}
