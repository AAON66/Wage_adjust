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

const SETTINGS_MODULE = { title: '账号设置', description: '查看账号信息并修改密码。', href: '/settings' };
const EMPLOYEE_ARCHIVE_MODULE = { title: '员工档案', description: '处理档案、绑定、导入和手册。', href: '/employee-admin' };
const IMPORT_CENTER_MODULE = { title: '导入中心', description: '模板下载、批量导入与结果追踪。', href: '/import-center' };

const ROLE_MODULES: Record<string, WorkspaceModuleLink[]> = {
  admin: [
    { title: '员工评估', description: '查看员工与评估流转。', href: '/employees' },
    { title: '创建周期', description: '新建评估周期与预算。', href: '/cycles/create' },
    { title: '调薪模拟', description: '查看预算占用与建议方案。', href: '/salary-simulator' },
    { title: '审批中心', description: '处理待审批与历史记录。', href: '/approvals' },
    { title: '考勤管理', description: '查看考勤数据与飞书同步。', href: '/attendance' },
    { title: '组织看板', description: '查看分布、热力和 ROI。', href: '/dashboard' },
    { title: '平台账号', description: '管理账号与权限范围。', href: '/user-admin' },
    { title: '审计日志', description: '查看所有操作与变更记录。', href: '/audit-log' },
    EMPLOYEE_ARCHIVE_MODULE,
    IMPORT_CENTER_MODULE,
    SETTINGS_MODULE,
  ],
  hrbp: [
    { title: '员工评估', description: '查看评估进度与复核结果。', href: '/employees' },
    { title: '调薪模拟', description: '查看预算占用与建议方案。', href: '/salary-simulator' },
    { title: '审批中心', description: '处理待审批建议。', href: '/approvals' },
    { title: '考勤管理', description: '查看考勤数据与同步状态。', href: '/attendance' },
    { title: '组织看板', description: '查看组织分布与人才表现。', href: '/dashboard' },
    { title: '平台账号', description: '管理员工账号。', href: '/user-admin' },
    EMPLOYEE_ARCHIVE_MODULE,
    IMPORT_CENTER_MODULE,
    SETTINGS_MODULE,
  ],
  manager: [
    { title: '员工评估', description: '查看团队评估与材料。', href: '/employees' },
    { title: '审批中心', description: '处理分配给你的审批。', href: '/approvals' },
    { title: '组织看板', description: '查看团队分布与表现。', href: '/dashboard' },
    { title: '平台账号', description: '管理员工账号。', href: '/user-admin' },
    EMPLOYEE_ARCHIVE_MODULE,
    IMPORT_CENTER_MODULE,
    SETTINGS_MODULE,
  ],
  employee: [
    { title: '个人评估中心', description: '查看材料与评估进展。', href: '/my-review' },
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
