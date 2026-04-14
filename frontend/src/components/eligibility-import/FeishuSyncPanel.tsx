import { useCallback, useEffect, useState } from 'react';

import { FeishuFieldMapper } from './FeishuFieldMapper';
import {
  parseBitableUrl,
  fetchBitableFields,
  triggerFeishuSync,
  getSyncStatus,
} from '../../services/eligibilityImportService';
import type {
  EligibilityImportType,
  FeishuFieldInfo,
} from '../../services/eligibilityImportService';
import { checkFeishuConfigExists } from '../../services/feishuService';

interface FeishuSyncPanelProps {
  importType: EligibilityImportType;
  label: string;
  onResult: (result: unknown) => void;
}

const SYSTEM_FIELDS_BY_TYPE: Record<EligibilityImportType, string[]> = {
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
  const [isFetchingFields, setIsFetchingFields] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [configExists, setConfigExists] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    checkFeishuConfigExists()
      .then((exists) => { if (!cancelled) setConfigExists(exists); })
      .catch(() => { if (!cancelled) setConfigExists(false); });
    return () => { cancelled = true; };
  }, []);

  const systemFields = SYSTEM_FIELDS_BY_TYPE[importType];

  // Poll sync status when taskId is set
  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      try {
        const data = await getSyncStatus(taskId);
        if (cancelled) return;
        if (data.status === 'completed') {
          onResult(data.result);
          setTaskId(null);
          setIsSyncing(false);
        } else if (data.status === 'failed') {
          setErrorMessage(data.error ?? '同步任务执行失败。');
          setTaskId(null);
          setIsSyncing(false);
        } else {
          setTimeout(() => { void poll(); }, 2000);
        }
      } catch {
        if (!cancelled) {
          setErrorMessage('查询同步状态失败。');
          setTaskId(null);
          setIsSyncing(false);
        }
      }
    };
    void poll();
    return () => { cancelled = true; };
  }, [taskId, onResult]);

  const handleFetchFields = useCallback(async () => {
    if (!url.trim()) return;
    setIsFetchingFields(true);
    setErrorMessage(null);
    setFeishuFields([]);
    setConnections([]);
    setAppToken(null);
    setTableId(null);

    let parsedOk = false;
    try {
      const parsed = await parseBitableUrl(url.trim());
      parsedOk = true;
      setAppToken(parsed.app_token);
      setTableId(parsed.table_id);

      const fieldsResponse = await fetchBitableFields(parsed.app_token, parsed.table_id);
      setFeishuFields(fieldsResponse.fields);
    } catch (err) {
      if (!parsedOk) {
        setErrorMessage('无法解析多维表格 URL，请确认链接格式正确。支持格式：https://xxx.feishu.cn/base/{app_token}?table={table_id}');
      } else {
        setErrorMessage('获取飞书字段列表失败，请检查多维表格 URL 和飞书应用权限配置。');
      }
      void err;
    } finally {
      setIsFetchingFields(false);
    }
  }, [url, feishuFields.length, appToken]);

  const handleStartSync = useCallback(async () => {
    if (!appToken || !tableId || connections.length === 0) return;
    setIsSyncing(true);
    setErrorMessage(null);

    const fieldMapping: Record<string, string> = {};
    for (const conn of connections) {
      fieldMapping[conn.feishuField] = conn.systemField;
    }

    try {
      const response = await triggerFeishuSync(importType, appToken, tableId, fieldMapping);
      setTaskId(response.task_id);
    } catch (err) {
      setIsSyncing(false);
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('触发同步失败，请稍后重试。');
      }
    }
  }, [appToken, tableId, connections, importType]);

  const syncDisabled = connections.length === 0 || isSyncing;

  return (
    <section className="surface" style={{ padding: '16px 20px' }}>
      <p className="eyebrow">飞书多维表格同步</p>
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        从飞书多维表格同步{label}数据
      </h2>

      {/* Config missing banner */}
      {configExists === false ? (
        <div
          style={{
            marginBottom: 12,
            padding: '10px 14px',
            borderRadius: 6,
            background: 'var(--color-bg-subtle, #fafafa)',
            border: '1px solid var(--color-border, #e0e0e0)',
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          <strong>尚未配置飞书应用凭据。</strong>
          <span style={{ marginLeft: 4 }}>
            请先前往{' '}
            <a href="/feishu-config" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>
              飞书配置页面
            </a>{' '}
            填写 App ID 和 App Secret，然后返回此页面使用同步功能。
          </span>
        </div>
      ) : null}

      {/* URL input */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <input
          className="toolbar-input"
          type="text"
          placeholder="请输入飞书多维表格 URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          style={{ flex: 1 }}
          disabled={configExists === false}
        />
        <button
          className="action-secondary"
          type="button"
          disabled={!url.trim() || isFetchingFields || configExists === false}
          onClick={() => void handleFetchFields()}
        >
          {isFetchingFields ? '获取中...' : '获取字段'}
        </button>
      </div>

      {errorMessage ? (
        <p role="alert" style={{ marginBottom: 12, fontSize: 13, color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}

      {/* Skeleton loading */}
      {isFetchingFields ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: 40,
                background: 'var(--color-bg-subtle)',
                borderRadius: 6,
                width: '60%',
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
          ))}
        </div>
      ) : null}

      {/* Field mapper */}
      {feishuFields.length > 0 && !isFetchingFields ? (
        <div style={{ marginBottom: 12 }}>
          <FeishuFieldMapper
            feishuFields={feishuFields}
            systemFields={systemFields}
            connections={connections}
            onConnectionsChange={setConnections}
          />
        </div>
      ) : null}

      {/* Sync button + progress */}
      {feishuFields.length > 0 ? (
        <div>
          {syncDisabled && connections.length === 0 && !isSyncing ? (
            <p style={{ fontSize: 13, color: 'var(--color-steel)', marginBottom: 8 }}>
              请先建立至少一个字段映射关系，再开始同步。
            </p>
          ) : null}

          <button
            className="action-primary"
            type="button"
            disabled={syncDisabled}
            onClick={() => void handleStartSync()}
          >
            {isSyncing ? '同步中...' : '开始同步'}
          </button>

          {isSyncing ? (
            <p role="status" aria-live="polite" style={{ marginTop: 8, fontSize: 13, color: 'var(--color-steel)' }}>
              正在同步飞书数据...
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
