/**
 * Lightweight inline SVG icons for sidebar navigation.
 * Each icon is 16×16, stroke-based, using currentColor for theme compatibility.
 */

interface IconProps {
  size?: number;
  className?: string;
  /** B-4 修复：支持 UI-SPEC §6.2/§9 的 `<WarningIcon style={{...}}/>` / `<ChartIcon style={{...}}/>` 用法 */
  style?: React.CSSProperties;
}

const defaults: Required<Pick<IconProps, 'size'>> = { size: 16 };

function svg(props: IconProps, children: React.ReactNode) {
  const s = props.size ?? defaults.size;
  return (
    <svg
      className={props.className}
      width={s}
      height={s}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, ...props.style }}
    >
      {children}
    </svg>
  );
}

/** 🏠 角色首页 */
export function IconHome(p: IconProps = {}) {
  return svg(p, <><path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" /><polyline points="9 21 9 14 15 14 15 21" /></>);
}

/** 📋 员工评估 */
export function IconClipboard(p: IconProps = {}) {
  return svg(p, <><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><line x1="8" y1="11" x2="16" y2="11" /><line x1="8" y1="15" x2="13" y2="15" /></>);
}

/** 🔄 创建周期 */
export function IconRefreshCw(p: IconProps = {}) {
  return svg(p, <><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></>);
}

/** 💰 调薪模拟 */
export function IconDollar(p: IconProps = {}) {
  return svg(p, <><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>);
}

/** ✅ 审批中心 */
export function IconCheckSquare(p: IconProps = {}) {
  return svg(p, <><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>);
}

/** 📅 考勤管理 */
export function IconCalendar(p: IconProps = {}) {
  return svg(p, <><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /><rect x="7" y="14" width="3" height="3" rx="0.5" /></>);
}

/** 📊 组织看板 */
export function IconBarChart(p: IconProps = {}) {
  return svg(p, <><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /><line x1="3" y1="21" x2="21" y2="21" /></>);
}

/** 📜 审计日志 */
export function IconFileText(p: IconProps = {}) {
  return svg(p, <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="14" y2="17" /></>);
}

/** 👥 平台账号 */
export function IconUsers(p: IconProps = {}) {
  return svg(p, <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>);
}

/** 📂 员工档案 */
export function IconFolder(p: IconProps = {}) {
  return svg(p, <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />);
}

/** 📥 导入中心 */
export function IconDownload(p: IconProps = {}) {
  return svg(p, <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>);
}

/** 🔗 飞书配置 */
export function IconLink(p: IconProps = {}) {
  return svg(p, <><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></>);
}

/** 🔑 API Key */
export function IconKey(p: IconProps = {}) {
  return svg(p, <><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" /></>);
}

/** 🔔 Webhook */
export function IconBell(p: IconProps = {}) {
  return svg(p, <><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></>);
}

/** ⚙️ 设置 */
export function IconSettings(p: IconProps = {}) {
  return svg(p, <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></>);
}

/** 🛡️ 调薪资格 */
export function IconShield(p: IconProps = {}) {
  return svg(p, <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />);
}

/** 📝 个人评估 */
export function IconEdit(p: IconProps = {}) {
  return svg(p, <><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></>);
}

/** 🔗 文件共享 */
export function IconShare(p: IconProps = {}) {
  return svg(p, <><circle cx="17" cy="5" r="3" /><circle cx="17" cy="19" r="3" /><circle cx="7" cy="12" r="3" /><path d="M9.5 10.5L14.5 6.5M9.5 13.5L14.5 17.5" /></>);
}

/** 🔄 Phase 34: 重算档次按钮（loading 时套 animate-spin） */
export function RefreshIcon(p: IconProps = {}) {
  return svg(p, <><path d="M21 12a9 9 0 1 1-3.5-7.1" /><polyline points="21 4 21 10 15 10" /></>);
}

/** ⚠ Phase 34: 档次分布偏离警告横幅 */
export function WarningIcon(p: IconProps = {}) {
  return svg(p, <><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><circle cx="12" cy="17" r="0.5" /></>);
}

/** 📊 Phase 34: 空状态「立即生成档次」CTA 图标 */
export function ChartIcon(p: IconProps = {}) {
  return svg(p, <><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /><line x1="3" y1="21" x2="21" y2="21" /></>);
}

/** Icon name → component mapping */
export const NAV_ICONS: Record<string, (p?: IconProps) => React.JSX.Element> = {
  home: IconHome,
  clipboard: IconClipboard,
  'refresh-cw': IconRefreshCw,
  dollar: IconDollar,
  'check-square': IconCheckSquare,
  calendar: IconCalendar,
  'bar-chart': IconBarChart,
  'file-text': IconFileText,
  users: IconUsers,
  folder: IconFolder,
  download: IconDownload,
  link: IconLink,
  key: IconKey,
  bell: IconBell,
  settings: IconSettings,
  edit: IconEdit,
  shield: IconShield,
  share: IconShare,
};
