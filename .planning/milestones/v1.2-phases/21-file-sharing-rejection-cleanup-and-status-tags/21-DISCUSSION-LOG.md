# Phase 21: 文件共享拒绝清理与状态标签 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09T06:21:53Z
**Phase:** 21-文件共享拒绝清理与状态标签
**Areas discussed:** 清理后历史保留、待同意标签出现位置、拒绝后的重复申请规则、超时后的用户提示

---

## 清理后历史保留

| Option | Description | Selected |
|--------|-------------|----------|
| 保留历史记录 | 副本删除后，`/sharing-requests` 仍保留 `rejected / expired` 历史，供双方查看 | ✓ |
| 连历史一起删除 | 副本和 sharing request 一起彻底删除，不保留痕迹 | |
| 只对申请者保留历史 | 原上传者端不再看到终态历史 | |

**User's choice:** 按推荐方案走，保留历史记录。  
**Notes:** 需要满足系统“可审计、可追溯”的核心价值，不能因为自动删除副本就把申请事实一起抹掉。

---

## 待同意标签出现位置

| Option | Description | Selected |
|--------|-------------|----------|
| 申请者和管理端查看该员工材料时都显示 | 复用现有 `FileList`，员工自助页和管理端员工详情页看到一致标签 | ✓ |
| 只在申请者自己的文件列表显示 | 管理端查看该员工材料时不显示 | |
| 只在共享申请页显示 | 文件列表不显示标签，所有状态都留在 `/sharing-requests` | |

**User's choice:** 按推荐方案走，在申请者文件列表及管理员查看该员工材料时都显示。  
**Notes:** `FileList` 当前被 `MyReview` 和 `EvaluationDetail` 复用，这个选择等价于锁定两个页面都要显示。

---

## 拒绝后的重复申请规则

| Option | Description | Selected |
|--------|-------------|----------|
| 拒绝终局、超时可重试 | 拒绝后不允许再次申请；超时后可重新上传触发新申请 | ✓ |
| 拒绝和超时都可重试 | 两种终态都允许重新发起 | |
| 拒绝和超时都不可重试 | 一次结束后都不能再次申请 | |

**User's choice:** 按推荐方案走，拒绝仍终局，超时保留重试能力。  
**Notes:** 这延续了 Phase 16 的核心业务边界，只调整“副本是否自动清理”，不引入新的申请策略变化。

---

## 超时后的用户提示

| Option | Description | Selected |
|--------|-------------|----------|
| 只保留历史页记录 | 文件列表不做额外说明，用户自行去共享申请页理解原因 | |
| 只给当前页面提示 | 文件消失时给提示，但共享申请页不强调历史原因 | |
| 历史页记录 + 明确删除原因提示 | 同时保留 `expired` 历史，并在现有 UI 中明确告诉申请者副本因超时被清理 | ✓ |

**User's choice:** 按推荐方案走，两者都要。  
**Notes:** 目标是避免“文件突然消失像 bug”这类体验问题，同时不扩展到新的通知中心。

---

## the agent's Discretion

- “待同意”标签在文件行中的具体视觉位置与样式
- 超时删除原因采用 toast、inline hint、空状态说明还是其他现有表面承载
- 后端返回给文件列表的 sharing 状态衍生字段设计

## Deferred Ideas

None — 本次讨论没有引入新的 phase 外能力
