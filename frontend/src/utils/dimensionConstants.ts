// 后端 dimension_scores.dimension_code 实际存储的是短代码（TOOL/DEPTH/LEARN/SHARE/IMPACT），
// 同时兼容历史的长代码别名，避免老数据或其他页面引用时命中空映射导致雷达图全零原点。
export const DIMENSION_LABELS: Record<string, string> = {
  TOOL: 'AI工具掌握度',
  DEPTH: 'AI应用深度',
  LEARN: 'AI学习能力',
  SHARE: 'AI分享贡献',
  IMPACT: 'AI成果转化',
  // Legacy long codes — kept for backward compatibility
  TOOL_MASTERY: 'AI工具掌握度',
  APPLICATION_DEPTH: 'AI应用深度',
  LEARNING_ABILITY: 'AI学习能力',
  SHARING_CONTRIBUTION: 'AI分享贡献',
  OUTCOME_CONVERSION: 'AI成果转化',
};

export const DIMENSION_WEIGHTS: Record<string, number> = {
  TOOL: 0.15,
  DEPTH: 0.15,
  LEARN: 0.20,
  SHARE: 0.20,
  IMPACT: 0.30,
  TOOL_MASTERY: 0.15,
  APPLICATION_DEPTH: 0.15,
  LEARNING_ABILITY: 0.20,
  SHARING_CONTRIBUTION: 0.20,
  OUTCOME_CONVERSION: 0.30,
};

// 雷达图固定顺序（UI-SPEC 五维度顺序）—— 对齐后端 DB 实际存的短代码
export const DIMENSION_ORDER = [
  'TOOL',
  'DEPTH',
  'LEARN',
  'SHARE',
  'IMPACT',
] as const;
