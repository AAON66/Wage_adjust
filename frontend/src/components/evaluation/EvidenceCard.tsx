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
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (Array.isArray(value)) return value.join(' / ');
  if (value == null) return '--';
  return String(value);
}

function splitEvidenceContent(content: string): string[] {
  const normalized = content.replace(/\s+/g, ' ').trim();
  if (!normalized) return [];
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
    <article style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-card)' }}>
      {/* Header */}
      <div style={{ borderBottom: '1px solid var(--color-border)', padding: '14px 20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
              <span style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)', borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 500 }}>
                {evidence.source_type}
              </span>
              <span style={{ border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 8px', fontSize: 12, color: 'var(--color-steel)' }}>
                {formatDate(evidence.created_at)}
              </span>
              {integrityFlagged ? (
                <span className="status-pill" style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger)' }}>需重点复核</span>
              ) : null}
            </div>
            <h3 style={{ marginTop: 8, fontSize: 16, fontWeight: 600, color: 'var(--color-ink)' }}>{evidence.title}</h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 8px', fontSize: 12, color: 'var(--color-steel)' }}>
              置信度 {confidence}
            </span>
            <button className="chip-button" onClick={() => setIsExpanded((c) => !c)} type="button">
              {isExpanded ? '收起' : '展开'}
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'grid' }} className="xl:grid-cols-[minmax(0,1fr)_260px]">
        {/* Summary */}
        <section style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>核心结论</p>
            <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>{summaryPoints.length || 1} 条摘要</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {visibleSummaryPoints.length ? (
              visibleSummaryPoints.map((point, index) => (
                <div key={`${evidence.id}-${index}`} style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 14px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ flexShrink: 0, width: 22, height: 22, borderRadius: '50%', background: 'var(--color-primary-light)', color: 'var(--color-primary)', fontSize: 11, fontWeight: 600, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {index + 1}
                  </span>
                  <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--color-ink)', minWidth: 0 }}>{truncateText(point, isExpanded ? 260 : 108)}</p>
                </div>
              ))
            ) : (
              <div style={{ border: '1px dashed var(--color-border)', borderRadius: 6, padding: '14px 16px', fontSize: 13, color: 'var(--color-steel)' }}>
                当前证据暂无可展示内容。
              </div>
            )}
          </div>

          {isExpanded && normalizedContent ? (
            <div style={{ marginTop: 12, background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-steel)' }}>原文摘录</p>
                <span style={{ fontSize: 12, color: 'var(--color-placeholder)' }}>便于复核上下文</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>{truncateText(normalizedContent, 520)}</p>
            </div>
          ) : null}
        </section>

        {/* Sidebar */}
        <aside style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-bg-subtle)', padding: '16px 20px' }} className="xl:border-l xl:border-t-0">
          {/* Metadata */}
          <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>证据快照</p>
              <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>快速扫描</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {visibleMetadata.length ? (
                visibleMetadata.map((item) => (
                  <div key={`${item.label}-${item.value}`} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, padding: '6px 10px', background: 'var(--color-bg-subtle)', borderRadius: 4, fontSize: 13 }}>
                    <span style={{ color: 'var(--color-steel)', flexShrink: 0 }}>{item.label}</span>
                    <span style={{ maxWidth: '58%', wordBreak: 'break-all', textAlign: 'right', fontWeight: 500, color: 'var(--color-ink)' }}>{truncateText(item.value, isExpanded ? 64 : 26)}</span>
                  </div>
                ))
              ) : (
                <div style={{ border: '1px dashed var(--color-border)', borderRadius: 4, padding: '10px 12px', fontSize: 13, color: 'var(--color-steel)' }}>
                  当前证据没有额外元信息。
                </div>
              )}
            </div>
          </div>

          {/* Tags */}
          {visibleTags.length ? (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 6, padding: '12px 14px', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>标签</p>
                <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>辅助定位主题</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {visibleTags.map((tag) => (
                  <span key={tag} style={{ border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 8px', fontSize: 12, color: 'var(--color-steel)', background: '#FFFFFF' }}>
                    {truncateText(tag, 24)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {hasMoreContent && !isExpanded ? (
            <div style={{ border: '1px dashed var(--color-border)', borderRadius: 6, padding: '10px 14px', fontSize: 12, lineHeight: 1.6, color: 'var(--color-steel)' }}>
              还有更多原文和元信息，展开后可查看完整上下文。
            </div>
          ) : null}
        </aside>
      </div>
    </article>
  );
}
