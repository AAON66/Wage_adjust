import type { FieldMappingItem } from '../../types/api';

interface FieldMappingTableProps {
  value: FieldMappingItem[];
  onChange: (mappings: FieldMappingItem[]) => void;
  readOnly?: boolean;
}

const SYSTEM_FIELDS = [
  'employee_no',
  'attendance_rate',
  'absence_days',
  'overtime_hours',
  'late_count',
  'early_leave_count',
] as const;

const SYSTEM_FIELD_LABELS: Record<string, { label: string; desc: string }> = {
  employee_no: { label: '员工工号（关联键）', desc: 'employee_no' },
  attendance_rate: { label: '出勤率', desc: 'attendance_rate' },
  absence_days: { label: '缺勤天数', desc: 'absence_days' },
  overtime_hours: { label: '加班时长（小时）', desc: 'overtime_hours' },
  late_count: { label: '迟到次数', desc: 'late_count' },
  early_leave_count: { label: '早退次数', desc: 'early_leave_count' },
};

function hasEmployeeNoMapping(mappings: FieldMappingItem[]): boolean {
  return mappings.some((m) => m.system_field === 'employee_no' && m.feishu_field.trim() !== '');
}

export function FieldMappingTable({ value, onChange, readOnly = false }: FieldMappingTableProps) {
  const missingEmployeeNo = !hasEmployeeNoMapping(value);

  function handleFeishuFieldChange(index: number, feishuField: string) {
    const updated = value.map((item, i) => (i === index ? { ...item, feishu_field: feishuField } : item));
    onChange(updated);
  }

  function handleSystemFieldChange(index: number, systemField: string) {
    const updated = value.map((item, i) => (i === index ? { ...item, system_field: systemField } : item));
    onChange(updated);
  }

  function handleAddRow() {
    onChange([...value, { feishu_field: '', system_field: '' }]);
  }

  function handleRemoveRow(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <div>
      <div className="table-shell">
        <table className="table-lite" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: '45%' }}>飞书字段名</th>
              <th style={{ width: '45%' }}>系统字段</th>
              {!readOnly ? <th style={{ width: '10%' }}></th> : null}
            </tr>
          </thead>
          <tbody>
            {value.map((item, index) => (
              <tr key={index}>
                <td>
                  {readOnly ? (
                    <span>{item.feishu_field}</span>
                  ) : (
                    <input
                      className="toolbar-input"
                      style={{ width: '100%' }}
                      type="text"
                      value={item.feishu_field}
                      onChange={(e) => handleFeishuFieldChange(index, e.target.value)}
                      placeholder="输入飞书字段名"
                    />
                  )}
                </td>
                <td>
                  {readOnly ? (
                    <div>
                      <div style={{ fontWeight: 500 }}>
                        {SYSTEM_FIELD_LABELS[item.system_field]?.label ?? item.system_field}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--color-steel)' }}>
                        {SYSTEM_FIELD_LABELS[item.system_field]?.desc ?? item.system_field}
                      </div>
                    </div>
                  ) : (
                    <select
                      className="toolbar-input"
                      style={{ width: '100%' }}
                      value={item.system_field}
                      onChange={(e) => handleSystemFieldChange(index, e.target.value)}
                    >
                      <option value="">选择系统字段</option>
                      {SYSTEM_FIELDS.map((field) => (
                        <option key={field} value={field}>
                          {SYSTEM_FIELD_LABELS[field].label}（{field}）
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                {!readOnly ? (
                  <td>
                    <button
                      className="chip-button"
                      onClick={() => handleRemoveRow(index)}
                      type="button"
                      style={{ color: 'var(--color-danger)', fontSize: 12 }}
                    >
                      删除
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!readOnly ? (
        <div className="mt-2" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="chip-button" onClick={handleAddRow} type="button">
            + 添加映射
          </button>
          {missingEmployeeNo ? (
            <span style={{ fontSize: 13, color: 'var(--color-danger)' }}>
              员工工号映射为必填项
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
