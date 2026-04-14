# Phase 21: 文件共享拒绝清理与状态标签 - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

在现有文件共享工作流上补齐两个收尾行为：当共享申请被拒绝或 72h 超时后，自动删除申请者上传的副本文件；当共享申请仍处于 pending 时，在申请者的文件列表里显示“待同意”状态标签。

本阶段不新增新的共享能力，不改 duplicate warning 的基本流程，也不引入新的通知系统或新的审批页面。

</domain>

<decisions>
## Implementation Decisions

### 拒绝 / 超时后的副本清理
- **D-01:** 当共享申请进入 `rejected` 或 `expired` 终态时，自动删除申请者副本，删除范围包括物理文件、`UploadedFile` 记录，以及该副本关联的 evidence / parse 衍生数据。
- **D-02:** 自动清理只影响申请者副本，不影响原上传者文件、原文件上的贡献关系，且不会误删共享申请历史记录。
- **D-03:** 即使副本被清理，共享申请记录仍保留在 `/sharing-requests` 里，作为双方都能查看的历史与审计轨迹。

### 待同意状态标签
- **D-04:** “待同意”标签显示在申请者副本所在的文件列表项上，而不是只留在共享申请页中。
- **D-05:** 由于 `FileList` 同时被 `MyReview` 和 `EvaluationDetail` 复用，管理员查看该员工材料时也应看到同一“待同意”标签。
- **D-06:** 该标签只表示共享申请状态仍为 `pending`，不扩展成新的解析状态体系，也不要求在原上传者自己的文件列表中镜像显示。

### 拒绝与超时后的再申请规则
- **D-07:** 拒绝仍然是终局结果；即使副本被自动删除，针对“相同 content_hash + 相同原上传者”的请求也不允许再次申请。
- **D-08:** 超时仍然允许重新发起；副本在超时后被自动删除，但申请者可以重新上传同一文件触发新的共享申请。

### 超时后的用户反馈
- **D-09:** 超时删除后，需要同时保留共享申请历史，并给申请者明确的删除原因反馈，避免用户只看到“文件消失”却不知道原因。
- **D-10:** 不新增独立通知中心、站内信或推送机制；超时反馈应落在现有页面与交互表面内完成。

### the agent's Discretion
- “待同意”标签在文件行中的具体摆放位置与视觉样式，只要与现有 `FileList` 风格一致即可。
- 超时删除原因的具体承载方式可由后续设计决定，例如 toast、inline hint、空状态说明或历史页提示，但必须清晰可见。
- 后端向前端暴露 pending sharing 状态时使用布尔字段、枚举字段或聚合显示字段，由后续 research / planning 决定。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` — Phase 21 goal、依赖关系和 4 条 success criteria
- `.planning/REQUIREMENTS.md` — `SHARE-06`, `SHARE-07`, `SHARE-08` 的正式需求映射
- `.planning/PROJECT.md` — v1.2 目标、审计导向和“不新增新能力”的产品边界
- `.planning/STATE.md` — 当前阶段位置与 session continuity

### Backend sharing lifecycle
- `backend/app/services/sharing_service.py` — 共享申请状态流转、72h 懒过期、approve/reject/revoke 行为
- `backend/app/api/v1/sharing.py` — 共享申请列表与审批接口，现有历史展示入口
- `backend/app/api/v1/files.py` — duplicate upload 原子建 request 的入口；后续副本清理与文件列表刷新需要与此链路兼容
- `backend/app/services/file_service.py` — 文件物理删除、evidence 清理、`delete_file()` 语义
- `backend/app/models/sharing_request.py` — `pending / approved / rejected / expired` 状态模型
- `backend/app/models/uploaded_file.py` — 副本文件实体与 `owner_contribution_pct`
- `backend/app/schemas/sharing.py` — sharing request API contract

### Frontend surfaces
- `frontend/src/components/evaluation/FileList.tsx` — 当前文件列表仅展示 parse status；Phase 21 的“待同意”标签要接入这里
- `frontend/src/pages/MyReview.tsx` — 申请者自助上传与文件列表页面
- `frontend/src/pages/EvaluationDetail.tsx` — 管理端查看员工材料时的共享上传与文件列表页面
- `frontend/src/pages/SharingRequests.tsx` — 共享申请历史页，Phase 21 仍保留为历史事实来源
- `frontend/src/components/sharing/SharingRequestCard.tsx` — 现有 sharing status pill 与操作区
- `frontend/src/services/fileService.ts` — 当前文件列表数据获取与删除操作
- `frontend/src/services/sharingService.ts` — sharing request list / reject / pending count API wrapper
- `frontend/src/App.tsx` — `/sharing-requests` 路由注册
- `frontend/src/utils/roleAccess.ts` — “共享申请”菜单项和角色可见性

### Regression coverage
- `backend/tests/test_api/test_sharing_api.py` — sharing API 原子性、权限和请求状态回归
- `backend/tests/test_submission/test_sharing_request.py` — sharing service 生命周期、reject / expired 语义和 lazy expiry 回归

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/sharing_service.py::_expire_stale_requests()`：已经把 72h 超时实现为查询时懒过期，Phase 21 可在这里接入“超时后副本清理”的收尾逻辑。
- `backend/app/services/file_service.py::delete_file()`：已经同时删除物理文件、evidence 和 DB 记录，是实现 reject / expire cleanup 的首选基础能力。
- `frontend/src/components/sharing/SharingRequestCard.tsx`：已有 `pending / approved / rejected / expired` pill，可复用视觉语言到文件列表标签。
- `frontend/src/pages/SharingRequests.tsx`：已有单独的历史页，不需要新建“已拒绝/已超时”历史承载面。
- `frontend/src/components/evaluation/FileList.tsx`：现有文件列表通用组件，适合作为“待同意”标签的统一显示面。

### Established Patterns
- 共享申请页与文件列表页是两个独立表面：前者展示申请生命周期，后者展示文件实体本身。
- duplicate upload 已经创建独立 `UploadedFile` 副本，而不是引用原文件，因此 reject / expire cleanup 应围绕申请者副本删除展开。
- 超时状态目前不是定时任务写回，而是 `list_requests()` / `get_pending_count()` 查询时懒过期。
- `FileList` 被 `MyReview` 和 `EvaluationDetail` 共用，因此任何文件行标签都会自然同时出现在员工自助页和管理端员工详情页。

### Integration Points
- `SharingService.reject_request()` 与 `_expire_stale_requests()` 是 reject / timeout cleanup 的主要后端接入点。
- `FileService.delete_file()` 或一个共享的底层删除 helper 需要避免把共享申请历史一起删掉。
- `UploadedFileRecord` / 文件列表 API 很可能需要新增 sharing 状态衍生字段，才能让 `FileList` 知道何时显示“待同意”。
- 前端在 reject / expire 后需要刷新文件列表与 sharing request 列表，确保副本消失和历史状态更新同时可见。

</code_context>

<specifics>
## Specific Ideas

- 本次讨论按推荐方案统一锁定，不再做额外分支探索。
- “待同意”是固定中文文案，不改成“待审批”或其他别名。
- 共享申请历史页继续作为“副本为何消失”的事实来源，不新建新的历史页。
- 这次阶段显式推翻了 Phase 16 中“拒绝后副本保留”的旧行为，但保留“拒绝不可重复申请、超时可重试”的核心规则。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-file-sharing-rejection-cleanup-and-status-tags*
*Context gathered: 2026-04-09*
