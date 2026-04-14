# Phase 23: 调薪资格统一导入管理 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 23-eligibility-import
**Areas discussed:** 页面结构与导航, 飞书多维表格集成, 导入结果展示, 入职信息与非法定假期数据模型

---

## 页面结构与导航

### 页面组织方式

| Option | Description | Selected |
|--------|-------------|----------|
| 新建独立页面 | 新建"调薪资格管理"页面，4 个 Tab，与 ImportCenter 分开 | |
| 复用 ImportCenter | 在现有 ImportCenter 加 4 个导入类型 | |
| 你来决定 | Claude 选择 | |

**User's choice:** 在原本的"调薪资格管理"页面里做增加，4 个 Tab。与 ImportCenter 分开
**Notes:** 用户明确指定在现有 EligibilityManagementPage 基础上扩展

### 导航入口

| Option | Description | Selected |
|--------|-------------|----------|
| 侧边栏菜单新增一项 | 在侧边栏添加"调薪资格管理"菜单项 | ✓ |
| 从现有页面跳转 | 从其他页面添加链接 | |

**User's choice:** 侧边栏菜单新增一项
**Notes:** 无

---

## 飞书多维表格集成

### 同步触发方式

| Option | Description | Selected |
|--------|-------------|----------|
| 手动触发 | HR 配置后点击"开始同步" | ✓ |
| 手动 + 定时 | 支持手动和定时同步 | |

**User's choice:** 手动触发
**Notes:** 无

### 凭证配置

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有 FeishuConfig | 复用 Settings 页面的飞书应用凭证 | ✓ |
| 每个 Tab 独立配置 | 每个数据类型独立配置凭证 | |

**User's choice:** 复用现有 FeishuConfig
**Notes:** 无

### 字段映射 UI

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 FieldMappingTable | 下拉选择模式 | |
| 新设计拖拽映射 | 拖拽连线方式 | ✓ |

**User's choice:** 新设计拖拽映射
**Notes:** 用户要求左右两栏拖拽连线，类似 ETL 工具

### 字段发现

| Option | Description | Selected |
|--------|-------------|----------|
| API 自动获取 | 输入 URL 后自动获取字段列表 | ✓ |
| 手动输入 | HR 手动输入字段名 | |

**User's choice:** API 自动获取
**Notes:** 无

### 限流策略

| Option | Description | Selected |
|--------|-------------|----------|
| 固定 RPM + 指数退避 | 复用 InMemoryRateLimiter 模式 | ✓ |
| 你来决定 | Claude 选择 | |

**User's choice:** 固定 RPM + 指数退避
**Notes:** 无

---

## 导入结果展示

### 展示方式

| Option | Description | Selected |
|--------|-------------|----------|
| 统计卡片 + 可展开错误表 | 复用 ImportResultPanel 模式 | ✓ |
| 全屏报告页 | 独立报告页面 | |

**User's choice:** 统计卡片 + 可展开错误表
**Notes:** 无

### 错误导出

| Option | Description | Selected |
|--------|-------------|----------|
| 需要导出 | CSV 包含行号+原因 | ✓ |
| 不需要 | 只在页面展示 | |

**User's choice:** 需要导出
**Notes:** 无

---

## 数据模型

### 入职信息

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 Employee 字段 | 更新 hire_date 等现有字段 | ✓ |
| 新建独立模型 | HireInfo 模型 | |

**User's choice:** 复用 Employee 字段
**Notes:** 无

### 非法定假期

| Option | Description | Selected |
|--------|-------------|----------|
| 新建模型 | NonStatutoryLeave: employee_no, year, total_days, leave_type | ✓ |
| 复用 AttendanceRecord | 扩展考勤记录 | |

**User's choice:** 新建模型
**Notes:** 无

---

## Claude's Discretion

- 拖拽连线前端库选择
- Tab 内布局排列
- 飞书 URL 解析逻辑
- NonStatutoryLeave 枚举值
- 数据冲突处理策略

## Deferred Ideas

None
