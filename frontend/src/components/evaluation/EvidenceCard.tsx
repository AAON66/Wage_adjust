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
  vision_quality_score: '视觉质量',
  vision_description: '图片描述',
  vision_dimension_relevance: '维度关联',
  slide_number: '幻灯片页码',
  image_source: '图片来源',
  vision_failed: '视觉评估',
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  vision_evaluation: '视觉评估',
  vision_failed: '视觉失败',
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatMetadataValue(key: string, value: unknown): string {
  // Vision-specific formatting per UI-SPEC
  if (key === 'slide_number' && typeof value === 'number') return `第 ${value} 页`;
  if (key === 'image_source') {
    if (value === 'ppt_embedded') return 'PPT 提取';
    if (value === 'standalone_upload') return '独立上传';
  }
  if (key === 'vision_failed') return value ? '失败' : '';
  if (key === 'vision_quality_score' && typeof value === 'number') return `${value}/5`;
  if (key === 'vision_description' && typeof value === 'string') return value.length > 80 ? `${value.slice(0, 80)}...` : value;
  if (key === 'vision_dimension_relevance' && typeof value === 'object' && value !== null) {
    const entries = Object.entries(value as Record<string, number>);
    if (entries.length === 0) return '--';
    return entries.map(([dim, score]) => `${dim} ${(score as number).toFixed(1)}`).join(', ');
  }
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
      value: formatMetadataValue(key, value),
    }));
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 75 ? 'var(--color-success)' : pct >= 50 ? 'var(--color-warning)' : 'var(--color-danger)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--color-border)' }}>
        <div style={{ height: 4, borderRadius: 2, width: `${pct}%`, background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color, minWidth: 32, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const summaryPoints = splitEvidenceContent(evidence.content);
  const normalizedContent = evidence.content.replace(/\s+/g, ' ').trim();
  const metadataRows = buildMetadataRows(evidence);
  const visibleSummaryPoints = isExpanded ? summaryPoints : summaryPoints.slice(0, 3);
  const visibleTags = isExpanded ? evidence.tags ?? [] : (evidence.tags ?? []).slice(0, 4);
  const visibleMetadata = isExpanded ? metadataRows : metadataRows.slice(0, 4);
  const hasMoreContent = summaryPoints.length > 3 || metadataRows.length > 4 || (evidence.tags?.length ?? 0) > 4 || normalizedContent.length > 220;
  const integrityFlagged = Boolean(evidence.metadata_json?.prompt_manipulation_detected);

  return (
    <article style={{ background: '#FFFFFF', border: `1px solid ${integrityFlagged ? 'var(--color-danger-border)' : 'var(--color-border)'}`, borderRadius: 8, overflow: 'hidden', boxShadow: 'var(--shadow-card)' }}>
      {/* Header */}
      <div style={{ borderBottom: '1px solid var(--color-border)', padding: '12px 16px', background: integrityFlagged ? 'var(--color-danger-bg)' : '#FFFFFF' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
              <span style={{
                background: evidence.source_type === 'vision_failed'
                  ? 'var(--color-danger-bg)'
                  : 'var(--color-primary-light)',
                color: evidence.source_type === 'vision_failed'
                  ? 'var(--color-danger)'
                  : 'var(--color-primary)',
                borderRadius: 4,
                padding: '1px 7px',
                fontSize: 11.5,
                fontWeight: 500,
                ...(evidence.source_type === 'vision_failed' ? {
                  border: '1px solid var(--color-danger-border, #FFCDD0)',
                } : {}),
              }}>
                {SOURCE_TYPE_LABELS[evidence.source_type] ?? evidence.source_type}
              </span>
              {integrityFlagged ? (
                <span className="status-pill" style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger)', border: '1px solid var(--color-danger-border)' }}>需重点复核</span>
              ) : null}
              <span style={{ fontSize: 11.5, color: 'var(--color-placeholder)' }}>
                {formatDate(evidence.created_at)}
              </span>
            </div>
            <h3 style={{ marginTop: 6, fontSize: 14, fontWeight: 600, color: 'var(--color-ink)', lineHeight: 1.4 }}>{evidence.title}</h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <button className="chip-button" onClick={() => setIsExpanded((c) => !c)} type="button">
              {isExpanded ? '收起' : '展开'}
            </button>
          </div>
        </div>
        {/* Confidence bar */}
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
            <span style={{ fontSize: 11.5, color: 'var(--color-steel)' }}>置信度</span>
          </div>
          <ConfidenceBar score={evidence.confidence_score} />
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'grid' }} className="xl:grid-cols-[minmax(0,1fr)_240px]">
        {/* Summary */}
        <section style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>核心结论</p>
            <span style={{ fontSize: 11.5, color: 'var(--color-placeholder)' }}>{summaryPoints.length || 1} 条</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {visibleSummaryPoints.length ? (
              visibleSummaryPoints.map((point, index) => (
                <div key={`${evidence.id}-${index}`} style={{ background: 'var(--color-bg-subtle)', borderRadius: 6, padding: '9px 12px', display: 'flex', alignItems: 'flex-start', gap: 9 }}>
                  <span style={{ flexShrink: 0, width: 18, height: 18, borderRadius: '50%', background: 'var(--color-primary-light)', color: 'var(--color-primary)', fontSize: 10, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginTop: 1 }}>
                    {index + 1}
                  </span>
                  <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--color-ink)', minWidth: 0 }}>{truncateText(point, isExpanded ? 260 : 108)}</p>
                </div>
              ))
            ) : (
              <div style={{ border: '1px dashed var(--color-border)', borderRadius: 6, padding: '12px 14px', fontSize: 13, color: 'var(--color-steel)' }}>
                当前证据暂无可展示内容。
              </div>
            )}
          </div>

          {isExpanded && normalizedContent ? (
            <div style={{ marginTop: 10, background: 'var(--color-bg-subtle)', borderRadius: 6, padding: '10px 12px' }}>
              <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-steel)', marginBottom: 6 }}>原文摘录</p>
              <p style={{ fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-steel)' }}>{truncateText(normalizedContent, 520)}</p>
            </div>
          ) : null}
        </section>

        {/* Sidebar */}
        <aside style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-bg-subtle)', padding: '14px 16px' }} className="xl:border-l xl:border-t-0">
          {/* Metadata */}
          <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px', marginBottom: 10 }}>
            <p style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>证据快照</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {visibleMetadata.length ? (
                visibleMetadata.map((item) => (
                  <div key={`${item.label}-${item.value}`} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--color-border)', fontSize: 12.5 }}>
                    <span style={{ color: 'var(--color-steel)', flexShrink: 0 }}>{item.label}</span>
                    <span style={{
                      maxWidth: '58%',
                      wordBreak: 'break-all',
                      textAlign: 'right',
                      fontWeight: 500,
                      color: item.label === '视觉质量'
                        ? (() => {
                            const score = Number(item.value.replace('/5', ''));
                            if (score >= 4) return 'var(--color-success)';
                            if (score >= 3) return 'var(--color-warning)';
                            return 'var(--color-danger)';
                          })()
                        : 'var(--color-ink)',
                      ...(item.label === '��觉质量' ? {
                        background: (() => {
                          const score = Number(item.value.replace('/5', ''));
                          if (score >= 4) return 'var(--color-success-bg, #E8FFEA)';
                          if (score >= 3) return 'var(--color-warning-bg, #FFF3E8)';
                          return 'var(--color-danger-bg, #FFECE8)';
                        })(),
                        borderRadius: 4,
                        padding: '1px 6px',
                      } : {}),
                    }}>
                      {truncateText(item.value, isExpanded ? 64 : 26)}
                    </span>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: 12.5, color: 'var(--color-placeholder)' }}>暂无元信息。</p>
              )}
            </div>
          </div>

          {/* Tags */}
          {visibleTags.length ? (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px', marginBottom: 10 }}>
              <p style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>标签</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {visibleTags.map((tag) => (
                  <span key={tag} style={{ border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 7px', fontSize: 11.5, color: 'var(--color-steel)', background: 'var(--color-bg-subtle)' }}>
                    {truncateText(tag, 24)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {hasMoreContent && !isExpanded ? (
            <button
              onClick={() => setIsExpanded(true)}
              type="button"
              style={{ width: '100%', border: '1px dashed var(--color-border)', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: 'var(--color-steel)', background: 'transparent', cursor: 'pointer', textAlign: 'center' }}
            >
              展开查看更多内容
            </button>
          ) : null}
        </aside>
      </div>
    </article>
  );
}
