import { useState } from 'react';

import { ImportResultPanel } from '../import/ImportResultPanel';
import { ExcelImportPanel } from './ExcelImportPanel';
import { FeishuSyncPanel } from './FeishuSyncPanel';
import type { EligibilityImportType } from '../../services/eligibilityImportService';
import type { ImportRowResult } from '../../types/api';

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

function normalizeResult(raw: unknown): ImportResult | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  return {
    totalRows: typeof obj.total_rows === 'number' ? obj.total_rows : 0,
    successRows: typeof obj.success_rows === 'number' ? obj.success_rows : 0,
    failedRows: typeof obj.failed_rows === 'number' ? obj.failed_rows : 0,
    rows: Array.isArray((obj.result_summary as Record<string, unknown>)?.rows)
      ? (obj.result_summary as Record<string, unknown>).rows as ImportRowResult[]
      : Array.isArray(obj.rows)
        ? obj.rows as ImportRowResult[]
        : [],
  };
}

export function ImportTabContent({ importType, label }: ImportTabContentProps) {
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const handleResult = (result: unknown) => {
    const normalized = normalizeResult(result);
    setImportResult(normalized);
  };

  const handleExportErrorReport = () => {
    // Future: download error report via API
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <ExcelImportPanel
        importType={importType}
        label={label}
        onResult={handleResult}
      />

      <FeishuSyncPanel
        importType={importType}
        label={label}
        onResult={handleResult}
      />

      {importResult ? (
        <ImportResultPanel
          totalRows={importResult.totalRows}
          successRows={importResult.successRows}
          failedRows={importResult.failedRows}
          rows={importResult.rows}
          onDownloadErrorReport={handleExportErrorReport}
        />
      ) : null}
    </div>
  );
}
