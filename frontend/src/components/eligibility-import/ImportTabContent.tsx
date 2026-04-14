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

  // Support both Excel import format (total_rows/success_rows/failed_rows)
  // and Feishu sync format (total/synced/skipped/failed)
  const totalRows = typeof obj.total_rows === 'number' ? obj.total_rows
    : typeof obj.total === 'number' ? obj.total : 0;
  const successRows = typeof obj.success_rows === 'number' ? obj.success_rows
    : typeof obj.synced === 'number' ? obj.synced : 0;
  const failedRows = typeof obj.failed_rows === 'number' ? obj.failed_rows
    : typeof obj.failed === 'number' ? obj.failed : 0;

  return {
    totalRows,
    successRows,
    failedRows,
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
