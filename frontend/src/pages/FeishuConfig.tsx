import { useEffect, useState } from 'react';

import axios from 'axios';

import { FieldMappingTable } from '../components/attendance/FieldMappingTable';
import { AppShell } from '../components/layout/AppShell';
import { createFeishuConfig, getFeishuConfig, updateFeishuConfig } from '../services/feishuService';
import type { FeishuConfigRead, FieldMappingItem } from '../types/api';

function HelpTip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span
      style={{ position: 'relative', display: 'inline-block', marginLeft: 6, cursor: 'help' }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <span
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 16, height: 16, borderRadius: '50%', fontSize: 11, fontWeight: 600,
          background: 'var(--color-border, #e0e0e0)', color: 'var(--color-steel, #666)',
        }}
      >?</span>
      {show && (
        <span
          style={{
            position: 'absolute', left: '50%', transform: 'translateX(-50%)',
            bottom: 'calc(100% + 6px)', width: 280, padding: '8px 10px',
            borderRadius: 6, fontSize: 12, lineHeight: 1.5,
            background: 'var(--color-surface-alt, #333)', color: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.18)', zIndex: 100, whiteSpace: 'pre-line',
          }}
        >{text}</span>
      )}
    </span>
  );
}

const FIELD_HELP: Record<string, string> = {
  app_id: '在飞书开放平台 → 你的应用 → 凭证与基础信息中获取「App ID」',
  app_secret: '在飞书开放平台 → 你的应用 → 凭证与基础信息中获取「App Secret」\n请妥善保管，更新后留空即保留原值',
  bitable_app_token: '打开多维表格 → 浏览器地址栏中 /base/ 后的那段字符串即为 App Token\n示例：https://xxx.feishu.cn/base/XxxAppToken',
  bitable_table_id: '打开多维表格 → 点击目标数据表 → 地址栏中 table= 后的字符串即为 Table ID\n示例：...?table=tblXxxTableId',
};

const DEFAULT_FIELD_MAPPINGS: FieldMappingItem[] = [
  { feishu_field: '', system_field: 'employee_no' },
  { feishu_field: '', system_field: 'attendance_rate' },
  { feishu_field: '', system_field: 'absence_days' },
  { feishu_field: '', system_field: 'overtime_hours' },
  { feishu_field: '', system_field: 'late_count' },
  { feishu_field: '', system_field: 'early_leave_count' },
  { feishu_field: '', system_field: 'leave_days' },
];

interface FormErrors {
  app_id?: string;
  app_secret?: string;
  bitable_app_token?: string;
  bitable_table_id?: string;
  sync_hour?: string;
  sync_minute?: string;
  field_mapping?: string;
}

export function FeishuConfigPage() {
  const [existingConfig, setExistingConfig] = useState<FeishuConfigRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});

  // Form state
  const [appId, setAppId] = useState('');
  const [appSecret, setAppSecret] = useState('');
  const [bitableAppToken, setBitableAppToken] = useState('');
  const [bitableTableId, setBitableTableId] = useState('');
  const [syncHour, setSyncHour] = useState(6);
  const [syncMinute, setSyncMinute] = useState(0);
  const [syncTimezone, setSyncTimezone] = useState('Asia/Shanghai');
  const [fieldMapping, setFieldMapping] = useState<FieldMappingItem[]>(DEFAULT_FIELD_MAPPINGS);

  useEffect(() => {
    async function loadConfig() {
      try {
        const config = await getFeishuConfig();
        setExistingConfig(config);
        setAppId(config.app_id);
        setBitableAppToken(config.bitable_app_token);
        setBitableTableId(config.bitable_table_id);
        setSyncHour(config.sync_hour);
        setSyncMinute(config.sync_minute);
        setSyncTimezone(config.sync_timezone);
        if (config.field_mapping.length > 0) {
          setFieldMapping(config.field_mapping);
        }
      } catch {
        // No config exists — use defaults (create mode)
      } finally {
        setIsLoading(false);
      }
    }
    void loadConfig();
  }, []);

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (!appId.trim()) errs.app_id = '请输入飞书 App ID';
    if (!existingConfig && !appSecret.trim()) errs.app_secret = '请输入飞书 App Secret';
    if (!bitableAppToken.trim()) errs.bitable_app_token = '请输入多维表格 App Token';
    if (!bitableTableId.trim()) errs.bitable_table_id = '请输入多维表格 Table ID';
    if (syncHour < 0 || syncHour > 23 || !Number.isInteger(syncHour)) errs.sync_hour = '请输入 0~23 之间的整数';
    if (syncMinute < 0 || syncMinute > 59 || !Number.isInteger(syncMinute)) errs.sync_minute = '请输入 0~59 之间的整数';
    const hasEmployeeNo = fieldMapping.some((m) => m.system_field === 'employee_no' && m.feishu_field.trim() !== '');
    if (!hasEmployeeNo) errs.field_mapping = '员工工号映射为必填项';
    return errs;
  }

  async function handleSave() {
    setSuccessMessage(null);
    setErrorMessage(null);
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setIsSaving(true);
    try {
      if (existingConfig) {
        // Update mode
        const updated = await updateFeishuConfig(existingConfig.id, {
          app_id: appId,
          app_secret: appSecret || undefined,
          bitable_app_token: bitableAppToken,
          bitable_table_id: bitableTableId,
          field_mapping: fieldMapping,
          sync_hour: syncHour,
          sync_minute: syncMinute,
          sync_timezone: syncTimezone,
        });
        setExistingConfig(updated);
        setAppSecret('');
        setSuccessMessage('配置已保存');
      } else {
        // Create mode
        const created = await createFeishuConfig({
          app_id: appId,
          app_secret: appSecret,
          bitable_app_token: bitableAppToken,
          bitable_table_id: bitableTableId,
          field_mapping: fieldMapping,
          sync_hour: syncHour,
          sync_minute: syncMinute,
          sync_timezone: syncTimezone,
        });
        setExistingConfig(created);
        setAppSecret('');
        setSuccessMessage('配置已创建');
      }
    } catch (err: unknown) {
      // EMPNO-03: 优先识别字段类型校验失败的 422 错误，给出具体文案
      if (axios.isAxiosError(err) && err.response?.status === 422) {
        const detail = err.response.data?.detail ?? err.response.data;
        if (detail && typeof detail === 'object' && detail.error === 'invalid_field_type') {
          const actual = detail.actual ?? '未知';
          const field = detail.field ?? 'employee_no';
          if (field === 'employee_no') {
            setErrorMessage(
              `工号字段类型必须为文本（当前为 ${actual}），请在飞书多维表格中将该字段改为「文本」类型后重试`,
            );
            setErrors((prev) => ({
              ...prev,
              field_mapping: '工号字段类型必须为文本',
            }));
          } else {
            setErrorMessage(`字段类型校验失败：${field} 应为文本，当前为 ${actual}`);
          }
          return;
        }
        if (detail && typeof detail === 'object' && detail.error === 'field_not_found_in_bitable') {
          setErrorMessage(
            `飞书多维表格中未找到字段「${detail.feishu_field_name ?? ''}」，请检查字段名是否拼写一致`,
          );
          return;
        }
        if (detail && typeof detail === 'object' && detail.error === 'bitable_fields_fetch_failed') {
          setErrorMessage(
            `无法校验飞书字段类型：${detail.message ?? '请稍后重试'}`,
          );
          return;
        }
      }
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('保存失败');
      }
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <AppShell title="飞书考勤配置" description="配置飞书应用凭证和字段映射，系统将据此从飞书多维表格同步考勤数据。">
        <div className="surface px-6 py-10" style={{ textAlign: 'center' }}>
          <p className="text-sm text-steel">正在加载配置...</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="飞书考勤配置" description="配置飞书应用凭证和字段映射，系统将据此从飞书多维表格同步考勤数据。">
      <div className="surface px-6 py-6 lg:px-7">
        {/* Connection config section */}
        <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 16, marginBottom: 20 }}>
          <p className="section-title" style={{ fontSize: 15, fontWeight: 600 }}>连接配置</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label htmlFor="feishu-app-id" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>App ID<HelpTip text={FIELD_HELP.app_id} /></label>
            <input
              className="toolbar-input"
              id="feishu-app-id"
              style={{ width: '100%' }}
              type="text"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
            />
            {errors.app_id ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.app_id}</p> : null}
          </div>

          <div>
            <label htmlFor="feishu-app-secret" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>App Secret<HelpTip text={FIELD_HELP.app_secret} /></label>
            <input
              className="toolbar-input"
              id="feishu-app-secret"
              style={{ width: '100%' }}
              type="password"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              placeholder={existingConfig ? '留空保留当前值' : ''}
            />
            {errors.app_secret ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.app_secret}</p> : null}
          </div>

          <div>
            <label htmlFor="feishu-bitable-app-token" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>多维表格 App Token<HelpTip text={FIELD_HELP.bitable_app_token} /></label>
            <input
              className="toolbar-input"
              id="feishu-bitable-app-token"
              style={{ width: '100%' }}
              type="text"
              value={bitableAppToken}
              onChange={(e) => setBitableAppToken(e.target.value)}
            />
            {errors.bitable_app_token ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.bitable_app_token}</p> : null}
          </div>

          <div>
            <label htmlFor="feishu-bitable-table-id" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>多维表格 Table ID<HelpTip text={FIELD_HELP.bitable_table_id} /></label>
            <input
              className="toolbar-input"
              id="feishu-bitable-table-id"
              style={{ width: '100%' }}
              type="text"
              value={bitableTableId}
              onChange={(e) => setBitableTableId(e.target.value)}
            />
            {errors.bitable_table_id ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.bitable_table_id}</p> : null}
          </div>

          <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="feishu-sync-hour" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>定时同步 - 时</label>
              <input
                className="toolbar-input"
                id="feishu-sync-hour"
                style={{ width: '100%' }}
                type="number"
                min={0}
                max={23}
                step={1}
                value={syncHour}
                onChange={(e) => setSyncHour(Number(e.target.value))}
              />
              {errors.sync_hour ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.sync_hour}</p> : null}
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="feishu-sync-minute" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>定时同步 - 分</label>
              <input
                className="toolbar-input"
                id="feishu-sync-minute"
                style={{ width: '100%' }}
                type="number"
                min={0}
                max={59}
                step={1}
                value={syncMinute}
                onChange={(e) => setSyncMinute(Number(e.target.value))}
              />
              {errors.sync_minute ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 4 }}>{errors.sync_minute}</p> : null}
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="feishu-sync-timezone" style={{ display: 'block', fontSize: 13.5, fontWeight: 600, marginBottom: 4 }}>时区</label>
              <select
                className="toolbar-input"
                id="feishu-sync-timezone"
                style={{ width: '100%' }}
                value={syncTimezone}
                onChange={(e) => setSyncTimezone(e.target.value)}
              >
                <option value="Asia/Shanghai">Asia/Shanghai</option>
                <option value="Asia/Tokyo">Asia/Tokyo</option>
                <option value="UTC">UTC</option>
              </select>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ borderTop: '1px solid var(--color-border)', margin: '24px 0' }} />

        {/* Field mapping section */}
        <div style={{ marginBottom: 16 }}>
          <p className="section-title" style={{ fontSize: 15, fontWeight: 600 }}>字段映射</p>
        </div>
        <FieldMappingTable value={fieldMapping} onChange={setFieldMapping} />
        {errors.field_mapping ? <p style={{ fontSize: 13, color: 'var(--color-danger)', marginTop: 8 }}>{errors.field_mapping}</p> : null}

        {/* Actions */}
        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="action-primary" disabled={isSaving} onClick={() => void handleSave()} type="button">
            {isSaving ? '保存中...' : '保存配置'}
          </button>
        </div>

        {successMessage ? (
          <p className="mt-3 text-sm" style={{ color: 'var(--color-success, #00B42A)' }}>{successMessage}</p>
        ) : null}
        {errorMessage ? (
          <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</p>
        ) : null}
      </div>
    </AppShell>
  );
}

export default FeishuConfigPage;
