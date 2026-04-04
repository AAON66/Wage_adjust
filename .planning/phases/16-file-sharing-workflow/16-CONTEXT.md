# Phase 16: File Sharing Workflow - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

上传与他人重复的文件时系统警告但允许继续，并自动发起共享申请，原上传者可审批/拒绝并协商贡献比例，超时自动标记为 expired。

</domain>

<decisions>
## Implementation Decisions

### 重复检测与警告交互
- **D-01:** 重复检测仅使用 content_hash（SHA-256），不考虑文件名。当前代码用 filename+content_hash，需改为仅 content_hash
- **D-02:** 前端使用 Modal 弹窗展示警告："此文件已由 [姓名] 于 [日期] 提交"，用户可选"继续上传"或"取消"
- **D-03:** 检测时机为文件选择后立即触发——前端计算 hash 后请求后端检查，上传按钮点击前就显示警告
- **D-04:** 批量上传时逐个文件弹窗警告，用户可逐个选择继续或跳过
- **D-05:** 用户确认"继续上传"后，文件存为新的 UploadedFile 副本（独立记录），不引用原文件

### 共享申请与审批流程
- **D-06:** 用户确认继续上传重复文件后，系统自动向原上传者发起共享申请（无需手动操作）
- **D-07:** 共享申请在专属"共享申请"页面展示（侧边栏新增菜单项），列出所有待审批/已处理的申请
- **D-08:** 审批页面展示：申请人姓名 + 文件名 + 申请日期 + 建议贡献比例，以及审批/拒绝按钮

### 共享申请数据模型
- **D-09:** 新建 SharingRequest 模型（新表），字段包含：requester_file_id, original_file_id, requester_submission_id, original_submission_id, status(pending/approved/rejected/expired), proposed_pct, final_pct, created_at, resolved_at
- **D-10:** 审批通过后自动在原文件上创建 ProjectContributor 记录，将申请者加为贡献者，评分自动生效

### 贡献比例协商规则
- **D-11:** 默认初始建议比例为 50:50 平分（申请者 50%，原上传者 50%）
- **D-12:** 原上传者审批时可在 1%-99% 范围内自由调整比例
- **D-13:** 审批通过后，文件产生的 EvidenceItem 分数按贡献比例加权分配给双方（复用已有 owner_contribution_pct 机制）

### 拒绝与已评估文件处理
- **D-14:** 原上传者拒绝后，申请者的文件保留在其提交中作为独立文件评分，不建立共享关系
- **D-15:** 同一对文件（相同 content_hash + 相同原上传者）只能申请一次，拒绝即终结，不允许重复申请
- **D-16:** 已评估完成的文件仍允许共享申请，审批通过后新比例在下次评估时生效，不追溯调整已完成的评估

### 超时处理机制
- **D-17:** 72小时超时使用查询时懒检测实现——每次查询共享申请列表时检查 created_at + 72h，超时则更新 status 为 expired
- **D-18:** 超时后仅状态变更为 expired，不发送额外通知，双方在列表中可看到
- **D-19:** 超时后申请者可通过重新上传同一文件触发新的共享申请（因为超时不等于拒绝）

### Claude's Discretion
- 前端 hash 计算的具体库选择（Web Crypto API 等）
- 共享申请 API 的具体路由设计
- Modal 弹窗的具体 UI 组件实现
- 侧边栏"共享申请"页面的路由和导航集成方式
- SharingRequest 的数据库迁移策略

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 文件服务
- `backend/app/services/file_service.py` — 现有 FileService，包含 _check_duplicate()（需修改匹配策略）、upload_files()（需改为警告而非拒绝）、_save_contributors()
- `backend/app/models/uploaded_file.py` — UploadedFile 模型，已有 content_hash 和 owner_contribution_pct
- `backend/app/models/project_contributor.py` — ProjectContributor 模型，审批通过后自动创建的关联记录

### 前端组件
- `frontend/src/components/evaluation/FileUploadPanel.tsx` — 现有文件上传面板，需增加重复检测和警告 Modal
- `frontend/src/components/evaluation/FileList.tsx` — 现有文件列表组件

### 需求文档
- `.planning/REQUIREMENTS.md` — SHARE-01, SHARE-02, SHARE-03, SHARE-04, SHARE-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileService._check_duplicate()`: 已有按 filename+content_hash 的查重，需改为仅 content_hash
- `FileService._compute_hash()`: SHA-256 哈希计算，可直接复用
- `FileService._save_contributors()`: 已有 ProjectContributor 创建逻辑，审批通过后可复用
- `UploadedFile.owner_contribution_pct`: 已有贡献比例字段，审批通过后更新此字段
- `UploadedFile.content_hash`: 已有索引字段，重复检测查询可高效执行

### Established Patterns
- 服务层继承模式：`__init__(self, db: Session, settings: Settings | None = None)`
- 模型混入：`UUIDPrimaryKeyMixin, CreatedAtMixin` 用于新表
- API 路由版本化：`/api/v1/...`
- 前端 Axios 服务层：`frontend/src/services/` 中每个域一个文件

### Integration Points
- `FileService.upload_files()` 需要改为返回重复信息而非抛异常
- 新建 `SharingService` 处理共享申请 CRUD 和审批逻辑
- 侧边栏导航需新增"共享申请"菜单项
- 新建前端页面 `SharingRequestsPage` 和对应路由

</code_context>

<specifics>
## Specific Ideas

- 前端 hash 计算可使用 Web Crypto API 的 `crypto.subtle.digest('SHA-256', buffer)` 实现
- 后端新增 `/api/v1/files/check-duplicate` 端点，接受 content_hash 返回是否重复及原上传者信息
- SharingRequest 的状态流转：pending → approved/rejected/expired（三个终态）
- 懒检测超时可在 SharingService.list_requests() 中实现：查询时先批量更新超时记录

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 16-file-sharing-workflow*
*Context gathered: 2026-04-04*
