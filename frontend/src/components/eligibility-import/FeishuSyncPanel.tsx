import { useCallback, useState } from 'react';

import { useTaskPolling } from '../../hooks/useTaskPolling';
import {
  parseBitableUrl,
  fetchBitableFields,
  triggerFeishuSync,
} from '../../services/eligibilityImportService';
import type {
  EligibilityImportType,
  FeishuFieldInfo,
} from '../../services/eligibilityImportService';
import { FeishuFieldMapper } from './FeishuFieldMapper';

interface FeishuSyncPanelProps {
  importType: EligibilityImportType;
  label: string;
  onResult: (result: unknown) => void;
}

const SYSTEM_FIELDS: Record<EligibilityImportType, string[]> = {
  performance_grades: ['employee_no', 'year', 'grade'],
  salary_adjustments: ['employee_no', 'adjustment_date', 'adjustment_type', 'amount'],
  hire_info: ['employee_no', 'hire_date'],
  non_statutory_leave: ['employee_no', 'year', 'total_days', 'leave_type'],
};

interface FieldConnection {
  feishuField: string;
  systemField: string;
}

export function FeishuSyncPanel({ importType, label, onResult }: FeishuSyncPanelProps) {
  const [url, setUrl] = useState('');
  const [appToken, setAppToken] = useState<string | null>(null);
  const [tableId, setTableId] = useState<string | null>(null);
  const [feishuFields, setFeishuFields] = useState<FeishuFieldInfo[]>([]);
  const [connections, setConnections] = useState<FieldConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number; errors: number } | null>(null);

  const taskStatus = useTaskPolling(taskId, {
    onComplete: (result) => {
      setTaskId(null);
      onResult(result);
    },
    onError: (errMsg) => {
      setTaskId(null);
      setError(errMsg);
    },
    onProgress: setProgress,
  });

  const isPolling = taskId !== null && taskStatus !== null && (taskStatus.status === 'pending' || taskStatus.status === 'running');

  const handleFetchFields = useCallback(async () => {
    if (!url.trim()) {
      setError('请输入飞书多维表格 URL');
      return;
    }
    setLoading(true);
    setError(null);
    setFeishuFields([]);
    setConnections([]);
    setAppToken(null);
    setTableId(null);

    try {
      const parseResp = await parseBitableUrl(url.trim());
      const { app_token, table_id } = parseResp.data;
      setAppToken(app_token);
      setTableId(table_id);

      const fieldsResp = await fetchBitableFields(app_token, table_id);
      setFeishuFields(fieldsResp.data.fields);
    } catch {
      setError('无法解析多维表格 URL，请检查链接格式是否正确');
    } finally {
      setLoading(false);
    }
  }, [url]);

  const handleSync = useCallback(async () => {
    if (!appToken || !tableId || connections.length === 0) return;

    setError(null);
    setProgress(null);

    const fieldMapping: Record<string, string> = {};
    for (const conn of connections) {
      fieldMapping[conn.feishuField] = conn.systemField;
    }

    try {
      const resp = await triggerFeishuSync(importType, appToken, tableId, fieldMapping);
      const data = resp.data as { task_id: string };
      setTaskId(data.task_id);
    } catch {
      setError('飞书同步触发失败，请重试');
    }
  }, [appToken, tableId, connections, importType]);

  const systemFields = SYSTEM_FIELDS[importType];

  return (
    <div>
      <p className="eyebrow">飞书多维表格同步</p>
      <h3 className="section-title" style={{ marginBottom: 12 }}>
        从飞书多维表格同步{label}数据
      </h3>

      {/* URL Input */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          className="toolbar-input"
          type="text"
          placeholder="粘贴飞书多维表格链接..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleFetchFields();
          }}
          style={{ flex: 1 }}
        />
        <button
          className="action-secondary"
          type="button"
          disabled={loading || !url.trim()}
          onClick={handleFetchFields}
        >
          获取字段
        </button>
      </div>

      {error && (
        <p style={{ marginBottom: 8, fontSize: 13, color: 'var(--color-danger)' }}>{error}</p>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: 20,
                borderRadius: 4,
                background: 'var(--color-border)',
                opacity: 0.5,
                animation: 'pulse 1.5s infinite',
              }}
            />
          ))}
        </div>
      )}

      {/* Field mapper */}
      {feishuFields.length > 0 && !loading && (
        <div style={{ marginBottom: 12 }}>
          <FeishuFieldMapper
            feishuFields={feishuFields}
            systemFields={systemFields}
            connections={connections}
            onConnectionsChange={setConnections}
          />
        </div>
      )}

      {/* Progress indicator */}
      {isPolling && (
        <p style={{ marginBottom: 8, fontSize: 13, color: 'var(--color-primary)' }}>
          {progress
            ? `正在同步飞书数据... 已处理 ${progress.processed}/${progress.total} 条`
            : '正在同步飞书数据...'}
        </p>
      )}

      {/* Sync button */}
      {feishuFields.length > 0 && !loading && (
        <div>
          <button
            className="action-primary"
            type="button"
            disabled={connections.length === 0 || isPolling}
            onClick={handleSync}
            title={connections.length === 0 ? '请先建立至少一个字段映射关系' : undefined}
          >
            开始同步
          </button>
          {connections.length === 0 && (
            <p style={{ marginTop: 4, fontSize: 12, color: 'var(--color-steel)' }}>
              请先建立至少一个字段映射关系，将左侧飞书字段拖拽到右侧系统字段
            </p>
          )}
        </div>
      )}
    </div>
  );
}
