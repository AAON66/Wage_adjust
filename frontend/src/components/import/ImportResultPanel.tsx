import type { ImportRowResult } from '../../types/api';
import { ImportErrorTable } from './ImportErrorTable';

interface ImportResultPanelProps {
  totalRows: number;
  successRows: number;
  failedRows: number;
  rows: ImportRowResult[];
  onDownloadErrorReport: () => void;
}

export function ImportResultPanel({
  totalRows,
  successRows,
  failedRows,
  rows,
  onDownloadErrorReport,
}: ImportResultPanelProps) {
  return (
    <section className="surface" style={{ padding: '16px 20px' }}>
      <p className="eyebrow">导入结果</p>
      <h2 className="section-title" style={{ marginBottom: 12 }}>本次导入完成</h2>

      <div className="metric-strip" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <article className="metric-tile">
          <p className="metric-label">总行数</p>
          <p className="metric-value" style={{ color: 'var(--color-ink)' }}>{totalRows}</p>
        </article>
        <article className="metric-tile">
          <p className="metric-label">成功</p>
          <p className="metric-value" style={{ color: 'var(--color-success)' }}>{successRows}</p>
        </article>
        <article className="metric-tile">
          <p className="metric-label">失败</p>
          <p className="metric-value" style={{ color: 'var(--color-danger)' }}>{failedRows}</p>
        </article>
      </div>

      {failedRows > 0 && successRows > 0 ? (
        <div
          role="alert"
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--color-warning-bg)',
            border: '1px solid var(--color-warning-border)',
            borderRadius: 8,
            fontSize: 13.5,
            lineHeight: 1.6,
            color: 'var(--color-ink)',
          }}
        >
          导入已完成，共 {totalRows} 条记录：{successRows} 条成功，{failedRows} 条失败。请查看下方错误明细或下载错误报告。
        </div>
      ) : null}

      {failedRows > 0 && successRows === 0 ? (
        <div
          role="alert"
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--color-danger-bg)',
            border: '1px solid var(--color-danger-border)',
            borderRadius: 8,
            fontSize: 13.5,
            lineHeight: 1.6,
            color: 'var(--color-ink)',
          }}
        >
          导入失败，{totalRows} 条记录全部未通过校验。请检查文件格式是否与模板一致，修正后重新导入。
        </div>
      ) : null}

      {failedRows === 0 ? (
        <p style={{ marginTop: 12, fontSize: 13.5, color: 'var(--color-success)' }}>
          导入完成，{successRows} 条记录全部成功。
        </p>
      ) : null}

      {failedRows > 0 ? (
        <>
          <ImportErrorTable rows={rows} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
            <button className="chip-button" onClick={onDownloadErrorReport} type="button">
              下载错误报告
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
