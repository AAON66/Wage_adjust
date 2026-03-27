# Phase 5: 文档去重与多作者 - 上下文 / Document Deduplication and Multi-Author - Context

**收集日期 / Gathered:** 2026-03-27
**状态 / Status:** 准备规划 / Ready for planning

<domain>
## 阶段边界 / Phase Boundary

防止员工重复提交证据材料，并支持协作项目在多个贡献者之间正确分配评估学分。

Prevent duplicate evidence submissions and correctly distribute evaluation credit across co-contributors for collaborative projects.

范围内 / In scope:
- 文件上传时的全局去重检测（文件名 + SHA-256 内容哈希） / Global deduplication on upload (filename + SHA-256 content hash)
- 多作者贡献度分配（上传者指定，总和 100%） / Multi-author contribution assignment (uploader assigns, must sum to 100%)
- 协作者异议机制 / Contributor dispute mechanism
- 补充材料上传（协作者可补充文件到共享项目） / Supplementary file upload by contributors
- 有效评分按贡献比例计算 / Effective score calculated by contribution percentage
- 审批视图展示协作者和贡献比例 / Approval view showing contributors and percentages

范围外 / Out of scope:
- 内容相似度检测（只做精确哈希匹配） / Content similarity detection (exact hash match only)
- 自动发现潜在协作者 / Auto-discovery of potential collaborators
- 跨周期去重豁免（如同一文件在新周期有新成果） / Cross-cycle dedup exemptions

</domain>

<decisions>
## 实施决策 / Implementation Decisions

### 去重策略 / Deduplication Strategy
- **D-01:** 去重判定标准为**文件名 + SHA-256 内容哈希**双重匹配。两者都相同才视为重复。
  Deduplication criteria: **filename + SHA-256 content hash** dual match. Both must match to be considered a duplicate.

- **D-02:** 去重范围为**全局**——跨员工、跨周期查重。不同人不能提交完全相同的文件。
  Deduplication scope is **global** — across employees and cycles. Different people cannot submit identical files.

- **D-03:** 检测到重复时**拒绝上传**，并显示"此文件已由 XXX 在 YYYY-MM-DD 提交"的提示信息，引用已有记录。
  On duplicate detection: **reject upload** and show "This file was already submitted by XXX on YYYY-MM-DD", referencing the existing record.

- **D-04:** 去重检测在**上传时实时发生**——文件选择后立即计算哈希并查重，拒绝在上传前完成。
  Dedup detection happens **in real-time on upload** — hash is computed immediately after file selection, rejection before upload completes.

### 贡献度分配 / Contribution Distribution
- **D-05:** 贡献度由**上传者分配**。上传文件时选择协作者并指定百分比，总和必须 100%。
  Contribution assigned by **uploader**. Select collaborators and assign percentages when uploading; must sum to 100%.

- **D-06:** 协作者**可以对分配比例提出异议**。异议需要全员确认或主管裁定。
  Contributors **can dispute** the assigned percentages. Disputes require all-member confirmation or manager adjudication.

- **D-07:** 贡献度在**提交评分前可修改**，提交评分后锁定。
  Contribution percentages are **modifiable until evaluation is submitted**, then locked.

- **D-08:** AI 评分乘以贡献比例计算有效分。项目 80 分、贡献 60% → 有效分 48。简单直观。
  Effective score = AI score × contribution percentage. Project 80pts, 60% contribution → 48pts effective. Simple and intuitive.

### 共享项目视图 / Shared Project View
- **D-09:** 协作者可以**查看共享项目 + 上传补充材料**，但不能删除原始文件。
  Contributors can **view shared project + upload supplementary files**, but cannot delete original files.

- **D-10:** 补充材料与原始文件**合并评分**——作为同一项目的证据一起进入 AI 评估。
  Supplementary materials are **scored together** with original files — they enter AI evaluation as evidence for the same project.

- **D-11:** 审批页面用**内联标签 + 贡献比例**展示多作者信息。每个协作者显示头像/名字 + 百分比标签。
  Approval page shows multi-author info with **inline tags + contribution percentages**. Each contributor displayed with avatar/name + percentage badge.

### Claude's Discretion / Claude 自行决定
- `content_hash` 字段的具体存储位置（UploadedFile 模型 vs 单独表）
- 异议流程的具体状态机设计
- 前端去重检测的具体 UX 交互细节（进度条、动画等）
- 补充材料与原始文件在 EvidenceItem 中的关联方式

</decisions>

<canonical_refs>
## 规范引用 / Canonical References

**下游代理在规划或实施前必须阅读以下文件。**
**Downstream agents MUST read these before planning or implementing.**

### 文件上传 / File Upload
- `backend/app/models/uploaded_file.py` — UploadedFile 模型（当前无 content_hash 字段，需新增）
- `backend/app/services/parse_service.py` — 文件解析服务，补充材料需接入
- `backend/app/parsers/` — 各类文件解析器

### 提交与证据 / Submission & Evidence
- `backend/app/models/submission.py` — EmployeeSubmission 模型
- `backend/app/models/evidence.py` — EvidenceItem 模型（需扩展多作者支持）
- `backend/app/services/evidence_service.py` — 证据服务

### 评估引擎 / Evaluation Engine
- `backend/app/engines/evaluation_engine.py` — 五维评分引擎（需接入贡献比例折算）
- `backend/app/services/evaluation_service.py` — 评估服务

### 审批 / Approval
- `frontend/src/pages/Approvals.tsx` — 审批页面（需添加多作者标签展示）

### 前端上传 / Frontend Upload
- `frontend/src/components/evaluation/FileUploadPanel.tsx` — 文件上传面板（需添加去重检测和协作者选择）

### 先前决策 / Prior Decisions
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — D-11: Alembic-only migrations

</canonical_refs>

<code_context>
## 现有代码洞察 / Existing Code Insights

### 可复用资产 / Reusable Assets
- `UploadedFile` 模型已有 `file_name`, `storage_key`, `file_type` 字段，可扩展 `content_hash`
- `EvidenceItem` 已有 `submission_id`, `source_type`, `confidence_score`，可扩展多作者关联
- `FileUploadPanel.tsx` 已有完整上传 UI，可扩展去重检测和协作者选择
- Phase 2 的 `compute_prompt_hash` SHA-256 工具可复用哈希计算模式

### 已建立模式 / Established Patterns
- Alembic 迁移用于所有 schema 变更
- 服务层注入模式（`__init__` 接收 `db`, `settings`, 可选依赖）
- 前端 axios 服务层封装所有 API 调用

### 集成点 / Integration Points
- 上传 API (`POST /api/v1/files/upload`) 需添加去重检查
- 评估生成时需按贡献比例折算有效分
- 审批列表序列化需包含协作者信息

</code_context>

<specifics>
## 具体要求 / Specific Ideas

- 全局去重：跨员工跨周期，不允许相同文件被不同人提交
- 上传时实时检测，不是后台异步检测
- 协作者可以异议分配比例，需要解决机制
- 补充材料与原始文件合并进入同一次 AI 评估
- 审批页面用内联标签展示，不用单独表格

</specifics>

<deferred>
## 延后事项 / Deferred Ideas

- 内容相似度检测（模糊匹配，如修改文件名后重新提交） — 需要额外算法，属于增强功能
- 自动发现潜在协作者（基于项目关键词匹配） — 新能力
- 跨周期去重豁免机制（同一文件在新周期有新进展时可重新提交） — 需要业务规则定义
- 协作者贡献度的历史趋势分析 — 属于看板/分析功能

</deferred>

---

*Phase: 05-document-deduplication-and-multi-author*
*Context gathered: 2026-03-27*
