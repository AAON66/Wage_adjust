import { useCallback, useState } from 'react';

import type { ImportRowResult } from '../../types/api';
import { ImportResultPanel } from '../import/ImportResultPanel';
import { ExcelImportPanel } from './ExcelImportPanel';
import { FeishuSyncPanel } from './FeishuSyncPanel';
import type { EligibilityImportType } from '../../services/eligibilityImportService';

interface ImportTabContentProps {
  importType: EligibilityImportType;
  label: string;
}

interface ImportResult {
  totalRows: number;
  successRows: number;
  failedRows: number;
  rows: ImportRowResult[];
}

function parseImportResult(raw: unknown): ImportResult | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  return {
    totalRows: typeof obj.total_rows === 'number' ? obj.total_rows : 0,
    successRows: typeof obj.success_rows === 'number' ? obj.success_rows : 0,
    failedRows: typeof obj.failed_rows === 'number' ? obj.failed_rows : 0,
    rows: Array.isArray(obj.rows) ? (obj.rows as ImportRowResult[]) : [],
  };
}

export function ImportTabContent({ importType, label }: ImportTabContentProps) {
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const handleResult = useCallback((result: unknown) => {
    const parsed = parseImportResult(result);
    setImportResult(parsed);
  }, []);

  const handleDownloadErrorReport = useCallback(() => {
    // Placeholder: future implementation would export errors as a file
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Excel Import */}
      <section className="surface" style={{ padding: '16px 20px' }}>
        <ExcelImportPanel importType={importType} label={label} onResult={handleResult} />
      </section>

      {/* Feishu Sync */}
      <section className="surface" style={{ padding: '16px 20px' }}>
        <FeishuSyncPanel importType={importType} label={label} onResult={handleResult} />
      </section>

      {/* Import Result */}
      {importResult && (
        <ImportResultPanel
          totalRows={importResult.totalRows}
          successRows={importResult.successRows}
          failedRows={importResult.failedRows}
          rows={importResult.rows}
          onDownloadErrorReport={handleDownloadErrorReport}
        />
      )}
    </div>
  );
}
