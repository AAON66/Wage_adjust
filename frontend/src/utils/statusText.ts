const STATUS_TEXT: Record<string, string> = {
  draft: '草稿',
  collecting: '收集中',
  submitted: '已提交',
  parsing: '解析中',
  parsed: '已解析',
  failed: '失败',
  generated: '已生成',
  evaluated: '已评估',
  reviewing: '复核中',
  pending_manager: '待主管评分',
  pending_hr: '待 HR 审核',
  returned: '已打回',
  confirmed: '已确认',
  calibrated: '已校准',
  pending: '待处理',
  recommended: '已建议',
  pending_approval: '待审批',
  approved: '已审批',
  rejected: '已驳回',
  locked: '已锁定',
  published: '已发布',
  archived: '已下架',
  active: '启用',
  inactive: '停用',
  completed: '已完成',
  queued: '排队中',
  processing: '处理中',
  'level 1': '一级',
  'level 2': '二级',
  'level 3': '三级',
  'level 4': '四级',
  'level 5': '五级',
};

export function formatStatusText(status: string | null | undefined, fallback = '--'): string {
  if (!status) {
    return fallback;
  }
  return STATUS_TEXT[status.trim().toLowerCase()] ?? status;
}

export function formatCycleStatus(status: string | null | undefined): string {
  return formatStatusText(status, '无');
}

export function formatAiLevel(level: string | null | undefined): string {
  return formatStatusText(level, '未生成');
}

export function formatParseStatus(status: string | null | undefined): string {
  return formatStatusText(status, '未解析');
}