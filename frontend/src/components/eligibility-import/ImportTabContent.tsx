import { useState } from 'react';

import { ImportResultPanel } from '../import/ImportResultPanel';
import { ExcelImportPanel } from './ExcelImportPanel';
import { FeishuSyncPanel } from './FeishuSyncPanel';
import type { EligibilityImportType } from '../../services/eligibilityImportService';
import type { ConfirmResponse, ImportRowResult } from '../../types/api';

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

/**
 * Phase 32 D-06：ExcelImportPanel 7 态机内部已 inline 显示 confirm 成功摘要
 * （done 分支：inserted/updated/no_change/failed 计数 + 「继续导入新文件」），
 * 因此不再需要把 ConfirmResponse 转给外层 ImportResultPanel。
 *
 * 此处 handleExcelComplete 仅做一次 console.info 留痕，便于排查双 Tab 场景；
 * 仍保留 ImportResultPanel 渲染给 FeishuSyncPanel（飞书同步沿用旧 Celery 路径）。
 */
function normalizeFeishuResult(raw: unknown): ImportResult | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  const totalRows = typeof obj.total === 'number' ? obj.total
    : typeof obj.total_rows === 'number' ? obj.total_rows : 0;
  const successRows = typeof obj.synced === 'number' ? obj.synced
    : typeof obj.success_rows === 'number' ? obj.success_rows : 0;
  const failedRows = typeof obj.failed === 'number' ? obj.failed
    : typeof obj.failed_rows === 'number' ? obj.failed_rows : 0;
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
  const [feishuResult, setFeishuResult] = useState<ImportResult | null>(null);

  const handleExcelComplete = (result: ConfirmResponse) => {
    // ExcelImportPanel 内部已显示 done 分支；此处仅留痕供调试
    console.info('Excel import completed', { importType, result });
  };

  const handleFeishuResult = (result: unknown) => {
    setFeishuResult(normalizeFeishuResult(result));
  };

  const handleExportErrorReport = () => {
    // Future: download error report via API
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <ExcelImportPanel
        importType={importType}
        label={label}
        onComplete={handleExcelComplete}
      />

      <FeishuSyncPanel
        importType={importType}
        label={label}
        onResult={handleFeishuResult}
      />

      {feishuResult ? (
        <ImportResultPanel
          totalRows={feishuResult.totalRows}
          successRows={feishuResult.successRows}
          failedRows={feishuResult.failedRows}
          rows={feishuResult.rows}
          onDownloadErrorReport={handleExportErrorReport}
        />
      ) : null}
    </div>
  );
}
