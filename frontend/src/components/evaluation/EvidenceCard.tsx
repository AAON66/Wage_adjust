import type { EvidenceRecord } from '../../types/api';

interface EvidenceCardProps {
  evidence: EvidenceRecord;
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const confidence = `${Math.round(evidence.confidence_score * 100)}%`;

  return (
    <article className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-ember">{evidence.source_type}</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">{evidence.title}</h3>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Confidence {confidence}</span>
      </div>
      <p className="mt-4 text-sm leading-7 text-slate-600">{evidence.content}</p>
      {evidence.tags?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {evidence.tags.map((tag) => (
            <span key={tag} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {tag}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}