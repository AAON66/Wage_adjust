# Phase 11: Menu & Navigation Restructuring — Context

**Status:** Ready for planning (gathered 2026-03-31)

---

## Phase Boundary

**In scope:**
- 侧边栏菜单从扁平列表重构为分组折叠结构
- 每角色的菜单分组和可见性配置
- 图标 + 分组标题 + 折叠/展开交互
- 折叠状态持久化 (localStorage)

**Out of scope:**
- URL 路由路径变更（所有现有 URL 不变，避免书签失效）
- 新页面创建（仅重新组织现有菜单项）
- 服务端菜单配置存储
- 拖拽排序菜单

---

## Implementation Decisions

### D-01: 分组方案 — 4 组

| 组名 | 菜单项 (admin) | 说明 |
|------|----------------|------|
| **运营管理** | 员工评估、创建周期、调薪模拟、审批中心、考勤管理 | 日常业务操作 |
| **数据分析** | 组织看板、审计日志 | 数据查看和监控 |
| **系统管理** | 平台账号、员工档案、导入中心、飞书配置、API Key 管理、Webhook 管理 | 系统配置和集成 |
| **个人** | 账号设置 | 不分组，直接放底部 |

### D-02: 视觉风格 — 图标 + 标题分组

- 每个菜单项前加文字图标 (emoji 或 SVG icon)
- 分组标题可点击折叠/展开
- 折叠时分组标题旁显示子项数量（如 `▶ 系统管理 (5)`）
- 展开时显示 `▼` 箭头，折叠时显示 `▶` 箭头
- 「个人」组不折叠，账号设置直接放侧边栏底部

### D-03: 折叠状态持久化 — localStorage

- key 格式: `nav_collapsed_{groupId}`（如 `nav_collapsed_operations`）
- 默认状态: 全部展开
- 刷新页面后恢复上次折叠状态

### D-04: 角色菜单映射

| 角色 | 可见分组 |
|------|----------|
| admin | 运营管理 + 数据分析 + 系统管理 + 个人 |
| hrbp | 运营管理 + 数据分析(仅看板) + 系统管理(部分) + 个人 |
| manager | 运营管理(部分) + 数据分析(仅看板) + 系统管理(部分) + 个人 |
| employee | 个人评估中心 + 个人 |

具体每角色可见项沿用现有 `ROLE_MODULES` 定义，只是加上分组归属。

### D-05: 数据结构变更

将 `ROLE_MODULES` 从 `Record<string, WorkspaceModuleLink[]>` 改为 `Record<string, MenuGroup[]>`：

```typescript
interface MenuGroup {
  id: string;           // 'operations' | 'analytics' | 'system'
  label: string;        // '运营管理' | '数据分析' | '系统管理'
  collapsible: boolean; // 个人组为 false
  items: WorkspaceModuleLink[];
}
```

### D-06: 飞书配置页归属 — 系统管理组

FeishuConfig 归入「系统管理」组，与 API Key 管理、Webhook 管理并列。

### D-07: 图标分配

| 菜单项 | 图标 |
|--------|------|
| 角色首页 | 🏠 |
| 员工评估 | 📋 |
| 创建周期 | 🔄 |
| 调薪模拟 | 💰 |
| 审批中心 | ✅ |
| 考勤管理 | 📅 |
| 组织看板 | 📊 |
| 审计日志 | 📜 |
| 平台账号 | 👥 |
| 员工档案 | 📂 |
| 导入中心 | 📥 |
| 飞书配置 | 🔗 |
| API Key 管理 | 🔑 |
| Webhook 管理 | 🔔 |
| 账号设置 | ⚙️ |
| 个人评估中心 | 📝 |

Claude 可根据实际渲染效果微调图标选择。

---

## Canonical References

| File | Purpose |
|------|---------|
| `frontend/src/utils/roleAccess.ts` | 当前 ROLE_MODULES 定义（重构目标） |
| `frontend/src/components/layout/AppShell.tsx` | ShellSidebar 渲染逻辑（重构目标） |
| `frontend/src/App.tsx` | 路由定义（不改动路由，仅确认菜单项对应） |

## Reusable Assets

- `WorkspaceModuleLink` 接口保留，扩展 `icon` 和 `group` 字段
- `getRoleModules` 函数签名变更为返回 `MenuGroup[]`
- `NavLink` 组件和 CSS 类保持不变

## Claude's Discretion

- 具体图标选择（emoji vs SVG，可根据渲染效果调整）
- 分组标题的 CSS 样式细节
- 折叠动画（是否加过渡动画）
- 空分组处理（某角色没有某组的任何项时不显示该组标题）
