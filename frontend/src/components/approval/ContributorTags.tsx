import type { ProjectContributorSummary } from '../../types/api';

interface ContributorTagsProps {
  contributors: ProjectContributorSummary[];
}

export function ContributorTags({ contributors }: ContributorTagsProps) {
  if (contributors.length === 0) {
    return null;
  }

  const sorted = [...contributors].sort((a, b) => b.contribution_pct - a.contribution_pct);

  // Group by file_name
  const byFile = new Map<string, ProjectContributorSummary[]>();
  for (const c of sorted) {
    const group = byFile.get(c.file_name) ?? [];
    group.push(c);
    byFile.set(c.file_name, group);
  }

  return (
    <div className="grid gap-3">
      {Array.from(byFile.entries()).map(([fileName, items]) => (
        <div key={fileName}>
          <p className="text-xs text-steel">{fileName}</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {items.map((item) => (
              <span
                key={`${item.employee_id}-${item.file_name}`}
                className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${
                  item.is_owner
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'border border-[var(--color-primary-border)] bg-[var(--color-primary-light,#eff6ff)] text-[var(--color-primary)]'
                }`}
              >
                {item.employee_name}
                <span className={`${item.is_owner ? 'text-white/80' : 'text-[var(--color-primary)]/70'}`}>
                  {item.contribution_pct}%
                </span>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
