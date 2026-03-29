interface EvaluationStepBarProps {
  currentStep: number;
}

const STEPS = ['已提交', '主管审核', 'HR 审核', '已完成'];

export function EvaluationStepBar({ currentStep }: EvaluationStepBarProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 0' }}>
      {STEPS.map((label, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        return (
          <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
            {/* Node */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 64 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 13,
                  fontWeight: 600,
                  backgroundColor: isCompleted
                    ? '#E8FFEA'
                    : isCurrent
                      ? '#1456F0'
                      : '#F2F3F5',
                  color: isCompleted
                    ? '#00B42A'
                    : isCurrent
                      ? '#FFFFFF'
                      : '#8F959E',
                }}
              >
                {isCompleted ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path
                      d="M11.5 3.5L5.5 10L2.5 7"
                      stroke="#00B42A"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <span
                style={{
                  marginTop: 6,
                  fontSize: 12,
                  fontWeight: isCurrent ? 600 : 400,
                  color: isCompleted
                    ? '#1F2329'
                    : isCurrent
                      ? '#1456F0'
                      : '#8F959E',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {index < STEPS.length - 1 && (
              <div
                style={{
                  width: 48,
                  height: 2,
                  backgroundColor: isCompleted ? '#00B42A' : '#E0E4EA',
                  marginBottom: 20,
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
