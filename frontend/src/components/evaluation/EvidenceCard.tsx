import { useState } from 'react';

import type { EvidenceRecord } from '../../types/api';

interface EvidenceCardProps {
  evidence: EvidenceRecord;
}

const METADATA_LABELS: Record<string, string> = {
  characters: '字符数',
  compressed: '压缩包',
  extension: '文件类型',
  file_id: '文件 ID',
  lines: '代码行数',
  pages: '页数',
  prompt_manipulation_detected: '诚信风险',
  source_file: '来源文件',
  storage_key: '存储路径',
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatMetadataValue(value: unknown): string {
  if (typeof value === 'boolean') {
    return value ? '是' : '否';
  }
  if (Array.isArray(value)) {
    return value.join(' / ');
  }
  if (value == null) {
    return '--';
  }
  return String(value);
}

function splitEvidenceContent(content: string): string[] {
  const normalized = content.replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return [];
  }

  const segments = normalized
    .split(/(?<=[。！？.!?;；])\s+|\s*\n+\s*/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 8);

  return segments.length ? segments : [normalized];
}

function truncateText(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength).trim()}...` : value;
}

function buildMetadataRows(evidence: EvidenceRecord): Array<{ label: string; value: string }> {
  return Object.entries(evidence.metadata_json ?? {})
    .filter(([key]) => !['file_id', 'storage_key'].includes(key))
    .slice(0, 6)
    .map(([key, value]) => ({
      label: METADATA_LABELS[key] ?? key,
      value: formatMetadataValue(value),
    }));
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const confidence = `${Math.round(evidence.confidence_score * 100)}%`;
  const summaryPoints = splitEvidenceContent(evidence.content);
  const normalizedContent = evidence.content.replace(/\s+/g, ' ').trim();
  const metadataRows = buildMetadataRows(evidence);
  const visibleSummaryPoints = isExpanded ? summaryPoints : summaryPoints.slice(0, 3);
  const visibleTags = isExpanded ? evidence.tags ?? [] : (evidence.tags ?? []).slice(0, 4);
  const visibleMetadata = isExpanded ? metadataRows : metadataRows.slice(0, 4);
  const hasMoreContent = summaryPoints.length > 3 || metadataRows.length > 4 || (evidence.tags?.length ?? 0) > 4 || normalizedContent.length > 220;
  const integrityFlagged = Boolean(evidence.metadata_json?.prompt_manipulation_detected);

  return (
    <article className="overflow-hidden rounded-[30px] border border-[#d8e3f6] bg-[linear-gradient(180deg,#ffffff_0%,#fbfdff_100%)] shadow-[0_22px_46px_rgba(15,23,42,0.05)]">
      <div className="border-b border-[#e7eef9] px-5 py-4 lg:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-[#eef4ff] px-3 py-1 text-xs font-semibold tracking-[0.02em] text-[#315fc9]">{evidence.source_type}</span>
              <span className="rounded-full border border-[#dbe6fb] bg-white px-3 py-1 text-xs text-[#5d79ab]">{formatDate(evidence.created_at)}</span>
              {integrityFlagged ? <span className="status-pill bg-rose-100 text-rose-700">需重点复核</span> : null}
            </div>
            <h3 className="mt-3 text-[22px] font-semibold tracking-[-0.03em] text-ink">{evidence.title}</h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[#eef3ff] px-3 py-1 text-xs font-semibold text-[#3159c7]">置信度 {confidence}</span>
            <button className="chip-button px-3 py-1 text-xs" onClick={() => setIsExpanded((current) => !current)} type="button">
              {isExpanded ? '收起详情' : '展开详情'}
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section className="px-5 py-5 lg:px-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-ink">核心结论</p>
              <p className="mt-1 text-sm text-steel">优先展示最值得判断的证据摘要。</p>
            </div>
            <span className="text-xs text-steel">{summaryPoints.length || 1} 条摘要</span>
          </div>

          <div className="mt-4 grid gap-3">
            {visibleSummaryPoints.length ? (
              visibleSummaryPoints.map((point, index) => (
                <div className="rounded-[24px] border border-[#dce6f5] bg-[linear-gradient(180deg,#f9fbff_0%,#f5f9ff_100%)] px-4 py-4" key={`${evidence.id}-${index}`}>
                  <div className="flex items-start gap-3">
                    <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#e7efff] text-xs font-semibold text-[#325fca]">
                      {index + 1}
                    </span>
                    <p className="min-w-0 text-sm leading-7 text-ink">{truncateText(point, isExpanded ? 260 : 108)}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-[24px] border border-dashed border-[#d8e4f7] bg-[#fbfdff] px-4 py-5 text-sm leading-7 text-steel">
                当前证据暂无可展示内容。
              </div>
            )}
          </div>

          {isExpanded && normalizedContent ? (
            <div className="mt-4 rounded-[24px] border border-[#dce6f5] bg-white px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs uppercase tracking-[0.16em] text-[#6b87d8]">原文摘录</p>
                <span className="text-xs text-steel">便于复核上下文</span>
              </div>
              <p className="mt-3 text-sm leading-7 text-steel">{truncateText(normalizedContent, 520)}</p>
            </div>
          ) : null}
        </section>

        <aside className="border-t border-[#e7eef9] bg-[linear-gradient(180deg,#fcfdff_0%,#f5f8ff_100%)] px-5 py-5 xl:border-l xl:border-t-0 xl:px-6">
          <div className="rounded-[24px] border border-white/80 bg-white/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-ink">证据快照</p>
              <span className="text-xs text-steel">快速扫描</span>
            </div>

            <div className="mt-4 space-y-2.5 text-sm">
              {visibleMetadata.length ? (
                visibleMetadata.map((item) => (
                  <div className="flex items-start justify-between gap-3 rounded-[18px] border border-[#dce6f5] bg-[#f8fbff] px-3 py-3" key={`${item.label}-${item.value}`}>
                    <span className="text-steel">{item.label}</span>
                    <span className="max-w-[58%] break-words text-right font-medium text-ink">{truncateText(item.value, isExpanded ? 64 : 26)}</span>
                  </div>
                ))
              ) : (
                <div className="rounded-[18px] border border-dashed border-[#dce6f5] px-3 py-4 text-steel">
                  当前证据没有额外元信息。
                </div>
              )}
            </div>
          </div>

          {visibleTags.length ? (
            <div className="mt-4 rounded-[24px] border border-white/80 bg-white/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-ink">标签</p>
                <span className="text-xs text-steel">辅助定位主题</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {visibleTags.map((tag) => (
                  <span key={tag} className="rounded-full border border-[#d9e5fb] bg-[#f8fbff] px-3 py-1 text-xs text-[#48638f]">
                    {truncateText(tag, 24)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {hasMoreContent && !isExpanded ? (
            <div className="mt-4 rounded-[20px] border border-dashed border-[#d4def3] px-4 py-4 text-xs leading-6 text-steel">
              这张证据还有更多原文和元信息，展开后可以继续查看完整上下文。
            </div>
          ) : null}
        </aside>
      </div>
    </article>
  );
}