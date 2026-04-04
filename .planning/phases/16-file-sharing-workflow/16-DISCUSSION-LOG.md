# Phase 16: File Sharing Workflow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 16-file-sharing-workflow
**Areas discussed:** 重复检测与警告交互, 共享申请与审批流程, 贡献比例协商规则, 超时处理机制, 拒绝后的处理逻辑, 共享申请数据模型, 已评估文件的共享限制

---

## 重复检测与警告交互

### 警告展示方式

| Option | Description | Selected |
|--------|-------------|----------|
| Modal 弹窗警告 | 上传时弹出 Modal 显示重复信息，用户可选继续或取消 | ✓ |
| Inline 警告条 | 文件列表中显示黄色警告条，不阻断流程 | |
| 两步确认 | 先 Inline 警告，再要求勾选确认 | |

**User's choice:** Modal 弹窗警告
**Notes:** 明确阻断流程，确保用户知情

### 匹配策略

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 content_hash | 只比较文件内容哈希，改名也能检测到 | ✓ |
| filename + content_hash | 保持现有逻辑 | |
| content_hash + 模糊匹配 | 主用 hash 辅以文件名相似度 | |

**User's choice:** 仅 content_hash

### 信息展示

| Option | Description | Selected |
|--------|-------------|----------|
| 姓名 + 日期 | 显示原上传者姓名和上传日期 | ✓ |
| 仅日期 | 保护原上传者隐私 | |
| 姓名 + 部门 + 日期 | 更多上下文 | |

**User's choice:** 姓名 + 日期

### 检测时机

| Option | Description | Selected |
|--------|-------------|----------|
| 文件选择后立即检测 | 前端算 hash 请求后端，上传前就警告 | ✓ |
| 点击上传时检测 | 后端检查，返回警告而非错误 | |
| 上传过程中检测 | 后端接收后检测，返回特殊状态码 | |

**User's choice:** 文件选择后立即检测

### 批量重复处理

| Option | Description | Selected |
|--------|-------------|----------|
| 逐个警告 | 每个重复文件单独弹窗确认 | ✓ |
| 汇总警告 | 所有重复文件一次性列出 | |
| 全部继续或全部取消 | 统一处理 | |

**User's choice:** 逐个警告

### 存储方式

| Option | Description | Selected |
|--------|-------------|----------|
| 存新副本 | 创建新的 UploadedFile 记录，各自独立 | ✓ |
| 引用原文件 | 通过 ProjectContributor 关联到原文件 | |

**User's choice:** 存新副本

---

## 共享申请与审批流程

### 通知位置

| Option | Description | Selected |
|--------|-------------|----------|
| 专属"共享申请"页面 | 侧边栏新增菜单项 | ✓ |
| 嵌入现有"我的文件"页 | 不新增页面 | |
| 全局通知铃铛 | 顶部导航栏通知图标 | |

**User's choice:** 专属"共享申请"页面

### 审批详情

| Option | Description | Selected |
|--------|-------------|----------|
| 申请人 + 文件名 + 日期 + 比例 | 完整信息加审批按钮 | ✓ |
| 包含文件预览 | 额外嵌入预览 | |
| 简洁卡片式 | 最简 | |

**User's choice:** 申请人 + 文件名 + 日期 + 比例

### 发起方式

| Option | Description | Selected |
|--------|-------------|----------|
| 自动发起 | 确认继续上传后自动发起 | ✓ |
| 手动确认 | 上传后显示按钮让用户选择 | |

**User's choice:** 自动发起

---

## 贡献比例协商规则

### 默认比例

| Option | Description | Selected |
|--------|-------------|----------|
| 50:50 平分 | 默认各 50% | ✓ |
| 原上传者 70% | 偏向原创者 | |
| 由申请者填写 | 申请者提出建议 | |

**User's choice:** 50:50 平分

### 调整范围

| Option | Description | Selected |
|--------|-------------|----------|
| 1%-99% 自由调整 | 只要双方都 > 0% | ✓ |
| 10%-90% 范围 | 限制极端分配 | |
| 固定档位选择 | 预设选项 | |

**User's choice:** 1%-99% 自由调整

### 评分影响

| Option | Description | Selected |
|--------|-------------|----------|
| 按比例加权证据分 | EvidenceItem 分数按比例分配 | ✓ |
| 双方全额分数 | 共享文件双方都计全分 | |
| You decide | Claude 决定 | |

**User's choice:** 按比例加权证据分

---

## 超时处理机制

### 实现方式

| Option | Description | Selected |
|--------|-------------|----------|
| 查询时懒检测 | 查询列表时检查并更新超时 | ✓ |
| 定时任务扫描 | Celery/cron 每小时扫描 | |
| 混合方式 | 懒检测 + 每日批量扫描 | |

**User's choice:** 查询时懒检测

### 超时通知

| Option | Description | Selected |
|--------|-------------|----------|
| 仅状态变更 | 不发送额外通知 | ✓ |
| 通知申请者 | 超时时通知申请者 | |
| 通知双方 | 超时时通知双方 | |

**User's choice:** 仅状态变更

### 重新申请

| Option | Description | Selected |
|--------|-------------|----------|
| 可以重新申请 | 重新上传触发新申请 | ✓ |
| 不允许 | 超时即终结 | |

**User's choice:** 可以重新申请（超时不等于拒绝）

---

## 拒绝后的处理逻辑

### 文件处理

| Option | Description | Selected |
|--------|-------------|----------|
| 文件保留但不关联 | 申请者文件作为独立文件评分 | ✓ |
| 文件自动删除 | 拒绝后移除 | |
| 标记为"未共享" | 保留并显示警告 | |

**User's choice:** 文件保留但不关联

### 重复申请

| Option | Description | Selected |
|--------|-------------|----------|
| 不允许重复申请 | 同一对文件只能申请一次 | ✓ |
| 允许一次重新申请 | 拒绝后可再申请一次 | |
| 无限制 | 可反复申请 | |

**User's choice:** 不允许重复申请

---

## 共享申请数据模型

### 模型选择

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 SharingRequest 模型 | 专用表，职责清晰 | ✓ |
| 复用 ProjectContributor | 扩展现有模型 | |

**User's choice:** 新建 SharingRequest 模型

### 审批后关联

| Option | Description | Selected |
|--------|-------------|----------|
| 自动创建 ProjectContributor | 审批通过后自动创建 | ✓ |
| 仅记录关系 | 不自动创建 | |

**User's choice:** 自动创建 ProjectContributor

---

## 已评估文件的共享限制

| Option | Description | Selected |
|--------|-------------|----------|
| 允许，但不追溯调整 | 新比例下次评估生效 | ✓ |
| 不允许 | 已评估文件不接受共享 | |
| 允许并追溯调整 | 自动重新计算 | |

**User's choice:** 允许，但不追溯调整

---

## Claude's Discretion

- 前端 hash 计算的具体库选择
- 共享申请 API 路由设计
- Modal 弹窗 UI 组件实现
- 侧边栏导航集成方式
- SharingRequest 数据库迁移策略

## Deferred Ideas

None — 讨论保持在阶段范围内
