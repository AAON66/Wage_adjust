import type { UserProfile } from '../types/api';

export interface WorkspaceModuleLink {
  title: string;
  description: string;
  href: string;
}

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  hrbp: 'HRBP',
  manager: '主管',
  employee: '员工',
};

const ROLE_HOME_PATHS: Record<string, string> = {
  admin: '/workspace',
  hrbp: '/workspace',
  manager: '/workspace',
  employee: '/my-review',
};

const SETTINGS_MODULE = { title: '账号设置', description: '修改个人密码；如为初始密码登录，需先在此完成改密。', href: '/settings' };

const ROLE_MODULES: Record<string, WorkspaceModuleLink[]> = {
  admin: [
    { title: '员工评估', description: '查看员工列表、详情与评估流转。', href: '/employees' },
    { title: '创建周期', description: '创建新的评估周期和预算计划。', href: '/cycles/create' },
    { title: '调薪模拟', description: '测算预算与建议涨幅的组合结果。', href: '/salary-simulator' },
    { title: '审批中心', description: '追踪待审批与历史审批状态。', href: '/approvals' },
    { title: '组织看板', description: '查看分布、热力和 ROI 快照。', href: '/dashboard' },
    { title: '导入中心', description: '下载模板、上传 CSV、查看任务结果。', href: '/import-center' },
    { title: '平台账号', description: '可管理员工、主管和 HRBP 账号；不能修改同级管理员。', href: '/user-admin' },
    SETTINGS_MODULE,
  ],
  hrbp: [
    { title: '员工评估', description: '查看员工评估进度与人工复核结果。', href: '/employees' },
    { title: '调薪模拟', description: '测算预算占用与建议方案。', href: '/salary-simulator' },
    { title: '审批中心', description: '处理待审批调薪建议。', href: '/approvals' },
    { title: '组织看板', description: '查看组织分布和高潜画像。', href: '/dashboard' },
    { title: '导入中心', description: '管理员工与材料导入任务。', href: '/import-center' },
    { title: '平台账号', description: '仅可管理员工账号，不能修改主管、HRBP 或管理员。', href: '/user-admin' },
    SETTINGS_MODULE,
  ],
  manager: [
    { title: '员工评估', description: '查看团队成员评估详情和材料准备情况。', href: '/employees' },
    { title: '审批中心', description: '处理分配给你的审批任务。', href: '/approvals' },
    { title: '组织看板', description: '查看团队在整体评估中的分布表现。', href: '/dashboard' },
    { title: '平台账号', description: '仅可管理员工账号，不能修改主管、HRBP 或管理员。', href: '/user-admin' },
    SETTINGS_MODULE,
  ],
  employee: [
    { title: '个人评估中心', description: '查看个人材料、评估状态和当前周期进展。', href: '/my-review' },
    SETTINGS_MODULE,
  ],
};

export function getRoleLabel(role: string | null | undefined): string {
  if (!role) return '未识别角色';
  return ROLE_LABELS[role] ?? role;
}

export function getRoleHomePath(role: string | null | undefined): string {
  if (!role) return '/login';
  return ROLE_HOME_PATHS[role] ?? '/workspace';
}

export function getRoleModules(role: string | null | undefined): WorkspaceModuleLink[] {
  if (!role) return [];
  return ROLE_MODULES[role] ?? [];
}

export function isAllowedRole(user: UserProfile | null, allowedRoles?: string[]): boolean {
  if (!user) return false;
  if (!allowedRoles || allowedRoles.length === 0) return true;
  return allowedRoles.includes(user.role);
}
