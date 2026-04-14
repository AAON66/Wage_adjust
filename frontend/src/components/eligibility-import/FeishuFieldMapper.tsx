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

interface LineCoords {
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
  const [lines, setLines] = useState<LineCoords[]>([]);
  const [draggingField, setDraggingField] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);

  const connectedFeishuFields = new Set(connections.map((c) => c.feishuField));
  const connectedSystemFields = new Set(connections.map((c) => c.systemField));

  const getSystemFieldLabel = (field: string): string => {
    return SYSTEM_FIELD_LABELS[field] ?? field;
  };

  const recalcLines = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const containerRect = container.getBoundingClientRect();

    const newLines: LineCoords[] = [];
    for (const conn of connections) {
      const leftEl = leftRefs.current.get(conn.feishuField);
      const rightEl = rightRefs.current.get(conn.systemField);
      if (!leftEl || !rightEl) continue;
      const leftRect = leftEl.getBoundingClientRect();
      const rightRect = rightEl.getBoundingClientRect();
      newLines.push({
        x1: leftRect.right - containerRect.left,
        y1: leftRect.top + leftRect.height / 2 - containerRect.top,
        x2: rightRect.left - containerRect.left,
        y2: rightRect.top + rightRect.height / 2 - containerRect.top,
        feishuField: conn.feishuField,
        systemField: conn.systemField,
      });
    }
    setLines(newLines);
  }, [connections]);

  useEffect(() => {
    recalcLines();

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
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, systemField: string) => {
      e.preventDefault();
      const feishuField = e.dataTransfer.getData('text/plain');
      if (!feishuField) return;

      // Remove existing connections for this feishu or system field
      const filtered = connections.filter(
        (c) => c.feishuField !== feishuField && c.systemField !== systemField,
      );
      filtered.push({ feishuField, systemField });
      onConnectionsChange(filtered);
      setDraggingField(null);
    },
    [connections, onConnectionsChange],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'link';
  }, []);

  const removeConnection = useCallback(
    (feishuField: string) => {
      onConnectionsChange(connections.filter((c) => c.feishuField !== feishuField));
    },
    [connections, onConnectionsChange],
  );

  const handleClearAll = useCallback(() => {
    if (!clearConfirm) {
      setClearConfirm(true);
      clearTimerRef.current = setTimeout(() => setClearConfirm(false), 3000);
      return;
    }
    if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    setClearConfirm(false);
    onConnectionsChange([]);
  }, [clearConfirm, onConnectionsChange]);

  // Keyboard accessible dropdown for connecting fields
  const handleKeyboardConnect = useCallback(
    (feishuField: string, systemField: string) => {
      const filtered = connections.filter(
        (c) => c.feishuField !== feishuField && c.systemField !== systemField,
      );
      filtered.push({ feishuField, systemField });
      onConnectionsChange(filtered);
      setDropdownOpen(null);
    },
    [connections, onConnectionsChange],
  );

  const getConnectionForFeishu = (feishuField: string): FieldConnection | undefined => {
    return connections.find((c) => c.feishuField === feishuField);
  };

  const getConnectionForSystem = (systemField: string): FieldConnection | undefined => {
    return connections.find((c) => c.systemField === systemField);
  };

  const availableSystemFields = systemFields.filter((sf) => !connectedSystemFields.has(sf));

  return (
    <div>
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          display: 'flex',
          gap: '4%',
        }}
      >
        {/* Left column: Feishu fields */}
        <div style={{ width: '48%' }}>
          <p
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--color-steel)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 8,
            }}
          >
            飞书字段
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {feishuFields.map((f) => {
              const conn = getConnectionForFeishu(f.field_name);
              const isConnected = !!conn;
              return (
                <div
                  key={f.field_id}
                  ref={(el) => {
                    if (el) leftRefs.current.set(f.field_name, el);
                    else leftRefs.current.delete(f.field_name);
                  }}
                  draggable="true"
                  onDragStart={(e) => handleDragStart(e, f.field_name)}
                  onDragEnd={handleDragEnd}
                  aria-label={
                    isConnected
                      ? `${f.field_name} 已映射到 ${getSystemFieldLabel(conn.systemField)}`
                      : `${f.field_name}，可拖拽映射`
                  }
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: `1px solid ${isConnected ? 'var(--color-primary-border, var(--color-primary))' : 'var(--color-border)'}`,
                    background: isConnected
                      ? 'var(--color-primary-light, rgba(59,130,246,0.05))'
                      : 'var(--color-surface, #fff)',
                    cursor: 'grab',
                    opacity: draggingField === f.field_name ? 0.5 : 1,
                    fontSize: 13.5,
                    color: 'var(--color-ink)',
                    transition: 'opacity 0.15s, background 0.15s',
                  }}
                >
                  <span>{f.field_name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {isConnected && (
                      <button
                        type="button"
                        onClick={() => removeConnection(f.field_name)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--color-steel)',
                          fontSize: 14,
                          lineHeight: 1,
                          padding: '0 4px',
                        }}
                        aria-label={`移除 ${f.field_name} 映射`}
                      >
                        x
                      </button>
                    )}
                    {/* Keyboard accessible connect button */}
                    {!isConnected && availableSystemFields.length > 0 && (
                      <div style={{ position: 'relative' }}>
                        <button
                          type="button"
                          onClick={() =>
                            setDropdownOpen(dropdownOpen === f.field_name ? null : f.field_name)
                          }
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--color-primary)',
                            fontSize: 11,
                            padding: '0 4px',
                          }}
                          aria-label={`连接 ${f.field_name} 到系统字段`}
                        >
                          连接到...
                        </button>
                        {dropdownOpen === f.field_name && (
                          <div
                            style={{
                              position: 'absolute',
                              top: '100%',
                              right: 0,
                              zIndex: 10,
                              background: 'var(--color-surface, #fff)',
                              border: '1px solid var(--color-border)',
                              borderRadius: 6,
                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                              minWidth: 140,
                            }}
                          >
                            {availableSystemFields.map((sf) => (
                              <button
                                key={sf}
                                type="button"
                                onClick={() => handleKeyboardConnect(f.field_name, sf)}
                                style={{
                                  display: 'block',
                                  width: '100%',
                                  textAlign: 'left',
                                  padding: '6px 12px',
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: 13,
                                  color: 'var(--color-ink)',
                                }}
                              >
                                {getSystemFieldLabel(sf)}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
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
          {lines.map((line) => (
            <line
              key={`${line.feishuField}-${line.systemField}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke="var(--color-primary)"
              strokeWidth={2}
              strokeLinecap="round"
            />
          ))}
        </svg>

        {/* Right column: System fields */}
        <div style={{ width: '48%' }}>
          <p
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--color-steel)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 8,
            }}
          >
            系统字段
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {systemFields.map((sf) => {
              const conn = getConnectionForSystem(sf);
              const isConnected = !!conn;
              return (
                <div
                  key={sf}
                  ref={(el) => {
                    if (el) rightRefs.current.set(sf, el);
                    else rightRefs.current.delete(sf);
                  }}
                  onDrop={(e) => handleDrop(e, sf)}
                  onDragOver={handleDragOver}
                  aria-label={
                    isConnected
                      ? `${getSystemFieldLabel(sf)} 已映射自 ${conn.feishuField}`
                      : `${getSystemFieldLabel(sf)}，可将飞书字段拖拽至此`
                  }
                  style={{
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: `1px solid ${isConnected ? 'var(--color-primary-border, var(--color-primary))' : 'var(--color-border)'}`,
                    background: isConnected
                      ? 'var(--color-primary-light, rgba(59,130,246,0.05))'
                      : 'var(--color-surface, #fff)',
                    fontSize: 13.5,
                    color: 'var(--color-ink)',
                    transition: 'background 0.15s',
                  }}
                >
                  {getSystemFieldLabel(sf)}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 12,
          fontSize: 13,
          color: 'var(--color-steel)',
        }}
      >
        <span>已建立 {connections.length} 个映射关系</span>
        {connections.length > 0 && (
          <button
            className="chip-button"
            type="button"
            onClick={handleClearAll}
          >
            {clearConfirm ? '确认清除？' : '清除全部映射'}
          </button>
        )}
      </div>
    </div>
  );
}
