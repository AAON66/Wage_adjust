import { useCallback, useEffect, useRef, useState } from 'react';

import type { FeishuFieldInfo } from '../../services/eligibilityImportService';

interface FieldConnection {
  feishuField: string;
  systemField: string;
}

interface FeishuFieldMapperProps {
  feishuFields: FeishuFieldInfo[];
  systemFields: string[];
  connections: FieldConnection[];
  onConnectionsChange: (connections: FieldConnection[]) => void;
}

const SYSTEM_FIELD_LABELS: Record<string, string> = {
  employee_no: '员工工号',
  year: '年度',
  grade: '绩效等级',
  adjustment_date: '调薪日期',
  adjustment_type: '调薪类型',
  amount: '调薪金额',
  hire_date: '入职日期',
  total_days: '假期天数',
  leave_type: '假期类型',
};

interface LineCoord {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  feishuField: string;
  systemField: string;
}

export function FeishuFieldMapper({
  feishuFields,
  systemFields,
  connections,
  onConnectionsChange,
}: FeishuFieldMapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const rightRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const [lineCoords, setLineCoords] = useState<LineCoord[]>([]);
  const [dragOverTarget, setDragOverTarget] = useState<string | null>(null);
  const [draggingField, setDraggingField] = useState<string | null>(null);
  const [hoverConnected, setHoverConnected] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectedFeishu = new Set(connections.map((c) => c.feishuField));
  const connectedSystem = new Set(connections.map((c) => c.systemField));

  const recalcLines = useCallback(() => {
    if (!containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const coords: LineCoord[] = [];

    for (const conn of connections) {
      const leftEl = leftRefs.current.get(conn.feishuField);
      const rightEl = rightRefs.current.get(conn.systemField);
      if (!leftEl || !rightEl) continue;

      const leftRect = leftEl.getBoundingClientRect();
      const rightRect = rightEl.getBoundingClientRect();

      coords.push({
        x1: leftRect.right - containerRect.left,
        y1: leftRect.top + leftRect.height / 2 - containerRect.top,
        x2: rightRect.left - containerRect.left,
        y2: rightRect.top + rightRect.height / 2 - containerRect.top,
        feishuField: conn.feishuField,
        systemField: conn.systemField,
      });
    }

    setLineCoords(coords);
  }, [connections]);

  useEffect(() => {
    recalcLines();
  }, [recalcLines]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      recalcLines();
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
    };
  }, [recalcLines]);

  const handleDragStart = useCallback((e: React.DragEvent, fieldName: string) => {
    e.dataTransfer.setData('text/plain', fieldName);
    e.dataTransfer.effectAllowed = 'link';
    setDraggingField(fieldName);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggingField(null);
    setDragOverTarget(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, sysField: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'link';
    setDragOverTarget(sysField);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOverTarget(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, systemField: string) => {
    e.preventDefault();
    setDragOverTarget(null);
    setDraggingField(null);

    const feishuField = e.dataTransfer.getData('text/plain');
    if (!feishuField) return;

    // Remove any existing connections for either field
    const filtered = connections.filter(
      (c) => c.feishuField !== feishuField && c.systemField !== systemField,
    );
    filtered.push({ feishuField, systemField });
    onConnectionsChange(filtered);
  }, [connections, onConnectionsChange]);

  const handleRemoveConnection = useCallback((feishuField: string) => {
    const filtered = connections.filter((c) => c.feishuField !== feishuField);
    onConnectionsChange(filtered);
  }, [connections, onConnectionsChange]);

  const handleClearAll = useCallback(() => {
    if (!clearConfirm) {
      setClearConfirm(true);
      clearTimerRef.current = setTimeout(() => {
        setClearConfirm(false);
      }, 3000);
      return;
    }
    setClearConfirm(false);
    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
      clearTimerRef.current = null;
    }
    onConnectionsChange([]);
  }, [clearConfirm, onConnectionsChange]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
      }
    };
  }, []);

  // Keyboard accessible connect via select
  const handleKeyboardConnect = useCallback((feishuField: string, systemField: string) => {
    if (!systemField) return;
    const filtered = connections.filter(
      (c) => c.feishuField !== feishuField && c.systemField !== systemField,
    );
    filtered.push({ feishuField, systemField });
    onConnectionsChange(filtered);
  }, [connections, onConnectionsChange]);

  const getConnectedSystem = (feishuField: string): string | undefined => {
    return connections.find((c) => c.feishuField === feishuField)?.systemField;
  };

  const getConnectedFeishu = (systemField: string): string | undefined => {
    return connections.find((c) => c.systemField === systemField)?.feishuField;
  };

  const availableSystemFields = systemFields.filter((f) => !connectedSystem.has(f));

  const fieldItemBase: React.CSSProperties = {
    padding: '12px 14px',
    borderRadius: 6,
    fontSize: 13.5,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    transition: 'background 0.12s, border-color 0.12s',
  };

  const connectedStyle: React.CSSProperties = {
    background: 'var(--color-primary-light)',
    border: '1px solid var(--color-primary-border)',
  };

  const defaultStyle: React.CSSProperties = {
    background: 'var(--color-bg-subtle)',
    border: '1px solid var(--color-border)',
  };

  const dragOverStyle: React.CSSProperties = {
    background: 'var(--color-primary-light)',
    border: '1px solid var(--color-primary)',
  };

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <div style={{ display: 'flex', gap: '4%' }}>
        {/* Left column - Feishu fields */}
        <div style={{ width: '48%' }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-steel)', marginBottom: 8 }}>
            飞书字段
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {feishuFields.map((field) => {
              const isConn = connectedFeishu.has(field.field_name);
              const mappedTo = getConnectedSystem(field.field_name);
              return (
                <div
                  key={field.field_id}
                  ref={(el) => {
                    if (el) leftRefs.current.set(field.field_name, el);
                    else leftRefs.current.delete(field.field_name);
                  }}
                  draggable
                  onDragStart={(e) => handleDragStart(e, field.field_name)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => isConn ? setHoverConnected(field.field_name) : undefined}
                  onMouseLeave={() => setHoverConnected(null)}
                  style={{
                    ...fieldItemBase,
                    ...(isConn ? connectedStyle : defaultStyle),
                    opacity: draggingField === field.field_name ? 0.5 : 1,
                    cursor: 'grab',
                  }}
                  aria-label={
                    isConn && mappedTo
                      ? `${field.field_name} 已映射到 ${SYSTEM_FIELD_LABELS[mappedTo] ?? mappedTo}`
                      : field.field_name
                  }
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {field.field_name}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                    {isConn && hoverConnected === field.field_name ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveConnection(field.field_name);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 2,
                          color: 'var(--color-danger)',
                          lineHeight: 1,
                        }}
                        aria-label={`移除 ${field.field_name} 的映射`}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    ) : null}
                    {/* Keyboard accessible connect */}
                    {!isConn && availableSystemFields.length > 0 ? (
                      <select
                        value=""
                        onChange={(e) => handleKeyboardConnect(field.field_name, e.target.value)}
                        aria-label={`连接 ${field.field_name} 到...`}
                        style={{
                          fontSize: 11,
                          padding: '2px 4px',
                          border: '1px solid var(--color-border)',
                          borderRadius: 4,
                          background: 'var(--color-bg-surface)',
                          color: 'var(--color-steel)',
                          cursor: 'pointer',
                          maxWidth: 80,
                        }}
                      >
                        <option value="">连接到...</option>
                        {availableSystemFields.map((sf) => (
                          <option key={sf} value={sf}>
                            {SYSTEM_FIELD_LABELS[sf] ?? sf}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right column - System fields */}
        <div style={{ width: '48%' }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-steel)', marginBottom: 8 }}>
            系统字段
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {systemFields.map((sysField) => {
              const isConn = connectedSystem.has(sysField);
              const mappedFrom = getConnectedFeishu(sysField);
              const isDragTarget = dragOverTarget === sysField;
              return (
                <div
                  key={sysField}
                  ref={(el) => {
                    if (el) rightRefs.current.set(sysField, el);
                    else rightRefs.current.delete(sysField);
                  }}
                  onDragOver={(e) => handleDragOver(e, sysField)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, sysField)}
                  onMouseEnter={() => isConn && mappedFrom ? setHoverConnected(mappedFrom) : undefined}
                  onMouseLeave={() => setHoverConnected(null)}
                  style={{
                    ...fieldItemBase,
                    ...(isDragTarget ? dragOverStyle : isConn ? connectedStyle : defaultStyle),
                  }}
                  aria-label={
                    isConn && mappedFrom
                      ? `${SYSTEM_FIELD_LABELS[sysField] ?? sysField} 已映射自 ${mappedFrom}`
                      : SYSTEM_FIELD_LABELS[sysField] ?? sysField
                  }
                >
                  <span>{SYSTEM_FIELD_LABELS[sysField] ?? sysField}</span>
                  {isConn && hoverConnected === mappedFrom ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (mappedFrom) handleRemoveConnection(mappedFrom);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 2,
                        color: 'var(--color-danger)',
                        lineHeight: 1,
                        flexShrink: 0,
                      }}
                      aria-label={`移除 ${SYSTEM_FIELD_LABELS[sysField] ?? sysField} 的映射`}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* SVG overlay for connection lines */}
      <svg
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      >
        {lineCoords.map((line) => (
          <line
            key={`${line.feishuField}-${line.systemField}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="var(--color-primary)"
            strokeWidth={2}
            strokeOpacity={hoverConnected === line.feishuField ? 0.6 : 1}
          />
        ))}
      </svg>

      {/* Status bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 12,
          padding: '8px 0',
          borderTop: '1px solid var(--color-border)',
        }}
      >
        <p style={{ fontSize: 13, color: 'var(--color-steel)', margin: 0 }}>
          已建立 {connections.length} 个映射关系
        </p>
        {connections.length > 0 ? (
          <button
            className="chip-button"
            type="button"
            onClick={handleClearAll}
          >
            {clearConfirm ? '确认清除？' : '清除全部映射'}
          </button>
        ) : null}
      </div>
    </div>
  );
}
