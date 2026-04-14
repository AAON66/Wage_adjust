import type { UserProfile } from '../types/api';

export interface WorkspaceModuleLink {
  title: string;
  description: string;
  href: string;
  icon: string;
}

export interface MenuGroup {
  id: string;
  label: string;
  collapsible: boolean;
  items: WorkspaceModuleLink[];
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

const SETTINGS_MODULE: WorkspaceModuleLink = { title: '账号设置', description: '查看账号信息并修改密码。', href: '/settings', icon: 'settings' };
const EMPLOYEE_ARCHIVE_MODULE: WorkspaceModuleLink = { title: '员工档案', description: '处理档案、绑定、导入和手册。', href: '/employee-admin', icon: 'folder' };
const IMPORT_CENTER_MODULE: WorkspaceModuleLink = { title: '导入中心', description: '模板下载、批量导入与结果追踪。', href: '/import-center', icon: 'download' };

const ROLE_MODULES: Record<string, MenuGroup[]> = {
  admin: [
    {
      id: 'operations',
      label: '运营管理',
      collapsible: true,
      items: [
        { title: '员工评估', description: '查看员工与评估流转。', href: '/employees', icon: 'clipboard' },
        { title: '创建周期', description: '新建评估周期与预算。', href: '/cycles/create', icon: 'refresh-cw' },
        { title: '调薪模拟', description: '查看预算占用与建议方案。', href: '/salary-simulator', icon: 'dollar' },
        { title: '审批中心', description: '处理待审批与历史记录。', href: '/approvals', icon: 'check-square' },
        { title: '调薪资格', description: '查看资格状态、特殊申请与数据导入管理。', href: '/eligibility', icon: 'shield' },
        { title: '考勤管理', description: '查看考勤数据与飞书同步。', href: '/attendance', icon: 'calendar' },
        { title: '共享申请', description: '查看和管理文件共享申请', href: '/sharing-requests', icon: 'share' },
      ],
    },
    {
      id: 'analytics',
      label: '数据分析',
      collapsible: true,
      items: [
        { title: '组织看板', description: '查看分布、热力和 ROI。', href: '/dashboard', icon: 'bar-chart' },
        { title: '审计日志', description: '查看所有操作与变更记录。', href: '/audit-log', icon: 'file-text' },
      ],
    },
    {
      id: 'system',
      label: '系统管理',
      collapsible: true,
      items: [
        { title: '平台账号', description: '管理账号与权限范围。', href: '/user-admin', icon: 'users' },
        EMPLOYEE_ARCHIVE_MODULE,
        IMPORT_CENTER_MODULE,
        { title: '飞书配置', description: '配置飞书应用凭证与同步。', href: '/feishu-config', icon: 'link' },
        { title: 'API Key 管理', description: '创建、轮换和撤销外部 API 访问密钥。', href: '/api-key-management', icon: 'key' },
        { title: 'Webhook 管理', description: '注册回调 URL，查看通知投递日志。', href: '/webhook-management', icon: 'bell' },
      ],
    },
  ],
  hrbp: [
    {
      id: 'operations',
      label: '运营管理',
      collapsible: true,
      items: [
        { title: '员工评估', description: '查看评估进度与复核结果。', href: '/employees', icon: 'clipboard' },
        { title: '调薪模拟', description: '查看预算占用与建议方案。', href: '/salary-simulator', icon: 'dollar' },
        { title: '审批中心', description: '处理待审批建议。', href: '/approvals', icon: 'check-square' },
        { title: '调薪资格', description: '查看资格状态、特殊申请与数据导入管理。', href: '/eligibility', icon: 'shield' },
        { title: '考勤管理', description: '查看考勤数据与同步状态。', href: '/attendance', icon: 'calendar' },
        { title: '共享申请', description: '查看和管理文件共享申请', href: '/sharing-requests', icon: 'share' },
      ],
    },
    {
      id: 'analytics',
      label: '数据分析',
      collapsible: true,
      items: [
        { title: '组织看板', description: '查看组织分布与人才表现。', href: '/dashboard', icon: 'bar-chart' },
      ],
    },
    {
      id: 'system',
      label: '系统管理',
      collapsible: true,
      items: [
        { title: '平台账号', description: '管理员工账号。', href: '/user-admin', icon: 'users' },
        EMPLOYEE_ARCHIVE_MODULE,
        IMPORT_CENTER_MODULE,
      ],
    },
  ],
  manager: [
    {
      id: 'operations',
      label: '运营管理',
      collapsible: true,
      items: [
        { title: '员工评估', description: '查看团队评估与材料。', href: '/employees', icon: 'clipboard' },
        { title: '审批中心', description: '处理分配给你的审批。', href: '/approvals', icon: 'check-square' },
        { title: '调薪资格', description: '查看资格状态与特殊申请。', href: '/eligibility', icon: 'shield' },
        { title: '共享申请', description: '查看和管理文件共享申请', href: '/sharing-requests', icon: 'share' },
      ],
    },
    {
      id: 'analytics',
      label: '数据分析',
      collapsible: true,
      items: [
        { title: '组织看板', description: '查看团队分布与表现。', href: '/dashboard', icon: 'bar-chart' },
      ],
    },
    {
      id: 'system',
      label: '系统管理',
      collapsible: true,
      items: [
        { title: '平台账号', description: '管理员工账号。', href: '/user-admin', icon: 'users' },
        EMPLOYEE_ARCHIVE_MODULE,
        IMPORT_CENTER_MODULE,
      ],
    },
  ],
  employee: [
    {
      id: 'personal',
      label: '个人',
      collapsible: false,
      items: [
        { title: '个人评估中心', description: '查看材料与评估进展。', href: '/my-review', icon: 'edit' },
        { title: '共享申请', description: '查看和管理文件共享申请', href: '/sharing-requests', icon: 'share' },
      ],
    },
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

export function getRoleModules(role: string | null | undefined): MenuGroup[] {
  if (!role) return [];
  return ROLE_MODULES[role] ?? [];
}

/** 将 MenuGroup[] 展平为 WorkspaceModuleLink[]，用于向后兼容 */
export function flattenMenuGroups(groups: MenuGroup[]): WorkspaceModuleLink[] {
  return groups.flatMap(g => g.items);
}

/** 获取账号设置模块（所有角色共享，固定在侧边栏底部） */
export function getSettingsModule(): WorkspaceModuleLink {
  return SETTINGS_MODULE;
}

export function isAllowedRole(user: UserProfile | null, allowedRoles?: string[]): boolean {
  if (!user) return false;
  if (!allowedRoles || allowedRoles.length === 0) return true;
  return allowedRoles.includes(user.role);
}
