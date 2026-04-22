---
phase: 32-eligibility-import-completion
plan: 05
subsystem: frontend-import
tags: [phase-32, frontend, typescript, types-contract, service-layer, preview-panel, ui-components, a11y, focus-trap, blob-download, deprecated, plan-06-ready]

# Dependency graph
requires:
  - phase: 32-eligibility-import-completion
    plan: 04
    provides: 4 个 HTTP 端点契约（POST /excel/preview / POST /excel/{job_id}/confirm / POST /excel/{job_id}/cancel / GET /excel/active）+ Pydantic schemas (PreviewResponse / ConfirmRequest / ConfirmResponse / ActiveJobResponse) + 409 错误顶层 body 约定（无 detail 包裹）
  - phase: 32-eligibility-import-completion
    plan: 03
    provides: backend/app/schemas/import_preview.py — 4 个 Pydantic v2 schemas + ImportJobStatus 含 'previewing' / 'cancelled'
provides:
  - frontend/src/types/api.ts 末尾追加 Phase 32 类型块（11 个新类型）：
    - EligibilityImportType / OverwriteMode / PreviewRowAction
    - FieldDiff / PreviewRow / PreviewCounters
    - PreviewResponse / ConfirmRequest / ConfirmResponse / ActiveJobResponse
    - ImportConflictDetail（409 body 顶层结构）
    - ImportJobStatus union 含 'previewing' / 'cancelled'（解决 Pitfall 2）
  - eligibilityImportService.ts 新增 5 个函数（对接 Plan 04 4 端点 + 模板下载）：
    - downloadTemplate(importType): blob 下载（D-05）
    - uploadAndPreview(importType, file, onUploadProgress?): preview 阶段
    - confirmImport(jobId, overwriteMode, confirmReplace?): 落库
    - cancelImport(jobId): 取消 previewing job
    - getActiveImportJob(importType): 查询活跃锁状态（D-18）
    - 旧 uploadEligibilityExcel + getTemplateUrl 标 @deprecated 保留
  - 6 个新 React 组件（最小 props，可独立复用）：
    - PreviewCountersStrip — 4 色计数卡片
    - PreviewDiffTable — 分页 + no_change 折叠 + 字段级 diff
    - OverwriteModeRadio — merge/replace + replace inline 警告
    - ReplaceModeConfirmModal — 二次确认（focus trap + ESC + 强制 checkbox）
    - ImportActiveJobBanner — Tab 顶部活跃 job 提示条
    - ImportPreviewPanel — 整合壳，受控 overwriteMode + modalOpen
affects: [32-06]

# Tech tracking
tech-stack:
  added: []  # 全部使用既有 stack（React 18 + TypeScript strict + Tailwind v3 + index.css 既有 token）
  patterns:
    - "TS 类型契约 1:1 对齐后端 Pydantic schemas（PreviewResponse / ConfirmRequest / ConfirmResponse / ActiveJobResponse）；ImportJobStatus union 显式包含 'previewing' + 'cancelled'，解决 Pitfall 2 stricter typing"
    - "Service blob 下载：复用 Phase 31 feishuService.downloadUnmatchedCsv 的 axios `responseType: 'blob'` + URL.createObjectURL + 临时 `<a download>` Safari 兼容模式"
    - "Service 旧函数 @deprecated 保留：Plan 06 改造前的过渡期 build 不中断；未来 phase 可移除"
    - "组件最小 props 原则：PreviewCountersStrip 只接 PreviewCounters 而不接整个 PreviewResponse；可在未来 Phase 34 绩效管理页面零成本复用"
    - "受控状态机：ImportPreviewPanel 持有 overwriteMode + modalOpen；OverwriteModeRadio / ReplaceModeConfirmModal 完全受控（每次 modal open 重置 acknowledged）"
    - "a11y 全套：role=dialog + aria-modal + aria-labelledby + aria-describedby + focus trap (Tab 循环) + ESC 关闭 + role=alert + role=status + role=group"
    - "破坏性操作双通道告警（视觉 + 文字 + 强制 checkbox）：replace 模式 inline 警告 + Modal 强制 checkbox 才能继续；后端 Plan 04 422 兜底（即使前端绕过仍拦截）"

key-files:
  created:
    - frontend/src/components/eligibility-import/PreviewCountersStrip.tsx
    - frontend/src/components/eligibility-import/PreviewDiffTable.tsx
    - frontend/src/components/eligibility-import/OverwriteModeRadio.tsx
    - frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx
    - frontend/src/components/eligibility-import/ImportActiveJobBanner.tsx
    - frontend/src/components/eligibility-import/ImportPreviewPanel.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/services/eligibilityImportService.ts

key-decisions:
  - "保留 getTemplateUrl + uploadEligibilityExcel 标 @deprecated（OQ4 决议）：Plan 06 改造完成前过渡期可同时存在，避免 build 中断；未来 phase 可清理"
  - "PreviewResponse.import_type 用 EligibilityImportType union 类型（不是 string）：与后端 ImportType enum 对齐，前端获得自动补全 + 错误检测"
  - "ConfirmResponse.status 用 Extract<ImportJobStatus, 'completed'|'partial'|'failed'>：从 union 派生窄化类型，禁止前端误处理 'previewing'/'pending' 等不可能状态"
  - "ActiveJobResponse.status 用 Extract<ImportJobStatus, 'previewing'|'processing'>：只有这两个状态算「活跃」，其他算 inactive"
  - "ImportPreviewPanel 选用内嵌面板（非抽屉）：Phase 31 抽屉用于「详情」，Preview 是主流程，内嵌符合 D-11 三步直线走完语义；UI-SPEC §「Open Questions」选择 2 已说明"
  - "ReplaceModeConfirmModal 每次 open 重置 acknowledged state：避免上次勾选残留导致误确认；首个 focus 落在 checkbox（focus trap 起点）"
  - "PreviewDiffTable.formatDiffValue 把 null/undefined/'' 显示为「(空)」：与 UI-SPEC § Copywriting 中「(空) → {new}」契约一致；conflict 行降级为「冲突原因未提供」防御 PreviewRow.conflict_reason 为 null 的边界"
  - "OverwriteModeRadio 选中态由父组件持有（受控）：方便 ImportPreviewPanel 监听变化触发 modal 弹出 / CTA 文案切换"

patterns-established:
  - "Plan 06 ExcelImportPanel 状态机改造可直接 import 这 6 个组件 + 5 个 service 函数；无需额外封装"
  - "Phase 34 绩效管理页面如需类似导入流程，可零成本复用 ImportPreviewPanel + 子组件（最小 props 设计）"
  - "未来导入 Preview 类型扩展：只需在 PreviewRowAction union 加新值 + ACTION_LABELS / ACTION_INDICATOR_VAR 加映射；表格 / 计数卡片自动 work"

requirements-completed: [IMPORT-02, IMPORT-05, IMPORT-06, IMPORT-07]

# Metrics
duration: 18min
completed: 2026-04-22
---

# Phase 32 Plan 05: 前端类型契约 + Preview 组件库 Summary

**Phase 32 前端基线建立：TypeScript 类型契约 1:1 对齐后端 + 5 个新 service 函数（含 blob 模板下载）+ 6 个独立可复用 React 组件（含 focus trap Modal）；Plan 06 ExcelImportPanel 状态机改造可直接拼装**

## Performance

- **Duration:** ~18 min（含上下文加载 + 组件实现 + lint/build 验证）
- **Tasks:** 2（Task 1 类型 + service；Task 2 6 个组件）
- **Files created/modified:** 8 (6 created + 2 modified)
- **Total LOC added:** ~990 行（类型 ~110 + service ~110 + 6 组件 ~770）

## Accomplishments

### Task 1: types/api.ts 扩展 + eligibilityImportService.ts 改造

**新增 11 个 TypeScript 类型（完全镜像后端 `backend/app/schemas/import_preview.py`）：**

| 类型 | 用途 | 后端对应 |
|---|---|---|
| `EligibilityImportType` | 4 类资格的 union | 后端 `import_type` 参数 enum |
| `ImportJobStatus` | 8 个状态的完整 union（含 'previewing' / 'cancelled'） | `ImportJob.status` 列 |
| `OverwriteMode` | 'merge' \| 'replace' | `ConfirmRequest.overwrite_mode` |
| `PreviewRowAction` | 4 个动作 union | `PreviewRow.action` |
| `FieldDiff` | { old, new } 字段级 diff | `FieldDiff` schema |
| `PreviewRow` | 行级 diff | `PreviewRow` schema |
| `PreviewCounters` | 4 色计数 | `PreviewCounters` schema |
| `PreviewResponse` | preview 端点返回 | `PreviewResponse` schema |
| `ConfirmRequest` | confirm 端点请求 | `ConfirmRequest` schema |
| `ConfirmResponse` | confirm 端点返回（status 用 Extract 窄化） | `ConfirmResponse` schema |
| `ActiveJobResponse` | GET /excel/active 返回（status 用 Extract 窄化） | `ActiveJobResponse` schema |
| `ImportConflictDetail` | 409 body 顶层结构（无 detail 包裹） | Plan 04 SUMMARY § Decision 4 |

**5 个新 service 函数：**

| 函数 | URL | 关键模式 |
|---|---|---|
| `downloadTemplate(importType)` | `GET /eligibility-import/templates/{type}?format=xlsx` | blob + URL.createObjectURL + `<a download>` |
| `uploadAndPreview(importType, file, onUploadProgress?)` | `POST /eligibility-import/excel/preview?import_type=X` | multipart/form-data + axios onUploadProgress + 120s timeout |
| `confirmImport(jobId, overwriteMode, confirmReplace?)` | `POST /eligibility-import/excel/{job_id}/confirm` | JSON body `{overwrite_mode, confirm_replace}` + 120s timeout |
| `cancelImport(jobId)` | `POST /eligibility-import/excel/{job_id}/cancel` | 无 body，后端返回 204；service 不返回值 |
| `getActiveImportJob(importType)` | `GET /eligibility-import/excel/active?import_type=X` | 默认 timeout（轻量查询） |

**Deprecated 标记保留：**

- `uploadEligibilityExcel(importType, file)` — 旧一步式上传（Plan 04 后端已 deprecated）
- `getTemplateUrl(importType): string` — 旧 URL 拼接（Pitfall 5: Safari `<a target=_blank>` 内嵌乱码）

保留理由：避免 Plan 06 改造前过渡期 build 错误；JSDoc `@deprecated` 让 IDE 自动 strikethrough 提示。

### Task 2: 6 个独立 UI 组件（最小 props 设计）

**子组件（5 个）：**

| 组件 | Props 签名 | 关键能力 |
|---|---|---|
| `PreviewCountersStrip` | `{ counters: PreviewCounters }` | 4 色 grid（insert/update/no_change/conflict）；0 值降级为 placeholder + bg-subtle；conflict>0 显示「需先修正」副标题；role=group + 每卡 role=status + aria-label |
| `PreviewDiffTable` | `{ rows: PreviewRow[], rowsTruncated?, truncatedCount? }` | 50/页分页（PAGE_SIZE）；no_change 默认折叠（chip-button 切换 + aria-expanded）；conflict 行红底高亮 + 左 3px 指示条 + aria-describedby 关联 conflict_reason；字段级 old → new 并排（line-through old + ink new）；空值占位 (空) |
| `OverwriteModeRadio` | `{ value: OverwriteMode, onChange, disabled? }` | fieldset+legend；merge 默认；replace 选中显示 inline 警告（role=alert + animate-fade-soft）；文案严格按 UI-SPEC（「合并模式（空值保留旧值，推荐）」/「替换模式（空值清空字段）」） |
| `ReplaceModeConfirmModal` | `{ open, totalRows, onClose, onConfirm }` | role=dialog + aria-modal + aria-labelledby + aria-describedby；focus trap（Tab/Shift+Tab 在 modal 内循环）；ESC 关闭；强制 checkbox「我已理解并确认」勾选才能点「继续（替换模式）」（disabled + tooltip）；点击遮罩关闭；点击内容 stopPropagation；每次 open 重置 acknowledged + 自动 focus 到 checkbox |
| `ImportActiveJobBanner` | `{ activeJob: ActiveJobResponse }` | 仅当 active=true 显示；STATUS_LABELS 中文映射（previewing→预览待确认 / processing→落库中）；显示 file_name + 开始时间；role=status + warning 配色 |

**整合壳（1 个）：**

| 组件 | Props 签名 | 关键状态机 |
|---|---|---|
| `ImportPreviewPanel` | `{ label, preview, onConfirm, onCancel, isConfirming? }` | 受控 `overwriteMode`（默认 merge）+ `modalOpen`；merge 直接调 onConfirm；replace 弹 modal → 勾选 → 调 onConfirm('replace')；conflict>0 时 CTA 禁用 + tooltip + aria-describedby（屏幕阅读器读出原因） |

**视觉契约严格落地：**

- 100% 复用 `index.css` 既有 token，**零新增 CSS 变量**
- 复用 class：`.surface` / `.section-title` / `.eyebrow` / `.metric-value` / `.table-lite` / `.table-shell` / `.chip-button` / `.action-primary` / `.action-secondary` / `.action-danger` / `.animate-fade-up` / `.animate-fade-soft`
- 颜色 token：`--color-success(-bg)(-border)` / `--color-info(-bg)` / `--color-primary-border` / `--color-steel` / `--color-bg-subtle` / `--color-border` / `--color-danger(-bg)(-border)` / `--color-warning(-bg)` / `--color-ink` / `--color-placeholder`

## Task Commits

| # | Commit | Type | Description |
|---|--------|------|-------------|
| 1 | `6756d3b` | feat(32-05) | Phase 32 前端 TS 类型契约 + 5 个新 service 函数 |
| 2 | `a141425` | feat(32-05) | 5 个独立 Preview UI 子组件 + ImportPreviewPanel 整合壳 |

## Files Created/Modified

### Created (6 files, ~770 LOC)

- `frontend/src/components/eligibility-import/PreviewCountersStrip.tsx` (121 行)
- `frontend/src/components/eligibility-import/PreviewDiffTable.tsx` (198 行)
- `frontend/src/components/eligibility-import/OverwriteModeRadio.tsx` (108 行)
- `frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx` (152 行)
- `frontend/src/components/eligibility-import/ImportActiveJobBanner.tsx` (45 行)
- `frontend/src/components/eligibility-import/ImportPreviewPanel.tsx` (142 行)

### Modified (2 files)

- `frontend/src/types/api.ts` — +106 行 / -1 行（末尾追加 Phase 32 类型块）
- `frontend/src/services/eligibilityImportService.ts` — +120 行 / -3 行（重写：保留旧函数 + 新增 5 个 + JSDoc deprecated）

## Decisions Made

### 1. ImportJobStatus union 含 'previewing' / 'cancelled' 而非扩展旧 ImportJobRecord.status

旧 `ImportJobRecord.status` (line 563) 定义为 `'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'partial'`，缺 'previewing' / 'cancelled'。

**方案：** 新建独立 `ImportJobStatus` union 含 7 个状态（去掉旧的 'queued'，加 'previewing' + 'cancelled'）；旧 `ImportJobRecord.status` 保持不变（一步式上传仍用 queued 路径）。

**理由：** 两阶段提交的状态机与旧 Celery 队列驱动的状态机不同；混入 'queued' 会让 ConfirmResponse / ActiveJobResponse 的 Extract<> 派生类型出现冗余；保持向后兼容。

### 2. ConfirmResponse.status 用 Extract<> 派生窄化

```typescript
status: Extract<ImportJobStatus, 'completed' | 'partial' | 'failed'>
```

而不是直接写字符串 union。

**理由：** 单一真相源（ImportJobStatus）；如果未来 backend 加新终态（如 'rolled_back'），只需在 ImportJobStatus 加，Extract 自动 work；前端代码使用时 IDE 提示更精确。

### 3. ImportConflictDetail 显式声明 409 body 顶层结构（无 detail 包裹）

来自 Plan 04 SUMMARY § Decision 4：`main.py http_exception_handler` 对 `HTTPException(detail=dict)` 直返 dict 作为 body，不嵌套 'detail' key。

**方案：** 类型定义为 `{ error: 'import_in_progress', import_type, message }`，前端 axios 错误拦截器可直接 `err.response?.data?.error === 'import_in_progress'` 判断。

### 4. PreviewDiffTable 字段级 diff 排版「old line-through → new bold」

UI-SPEC §「Diff 表格行内着色」契约：
- `old` 用 `--color-steel` + `text-decoration: line-through`
- 中间 `→` 用 `--color-steel`
- `new` 用 `--color-ink` + `font-weight: 600`

**实现：** `formatDiffValue` 把 null/undefined/'' 统一格式化为「(空)」（与 UI-SPEC § Copywriting 字段变更单元格 insert/update 文案契约对齐）。

### 5. ReplaceModeConfirmModal 每次 open 重置 acknowledged + auto-focus checkbox

```typescript
useEffect(() => {
  if (open) {
    setAcknowledged(false);
    const t = window.setTimeout(() => checkboxRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }
  return undefined;
}, [open]);
```

**理由：**
- 重置 acknowledged：避免用户「关闭→再打开」时残留 checked 状态导致误确认
- setTimeout 0：等 modal DOM 渲染完成后再 focus，确保 focus trap 起点正确
- 清理 setTimeout：避免在 modal 关闭后异步 focus 引起 React warning

### 6. ImportPreviewPanel 选用内嵌面板（非抽屉）

来自 UI-SPEC §「Open Questions」选择 2 的论证：
- Phase 31 抽屉用于「日志详情」（辅助视图）
- Preview 是主流程而非辅助视图（D-11「上传→预览→确认」3 步直线走完）
- 抽屉会让主流程隔层跳转，与 CONTEXT.md「不要太多步骤」原则冲突
- 未来 Phase 34 绩效管理页面复用时，内嵌更便于嵌入

**实现：** `<section className="surface animate-fade-up">` + 5 个子组件竖向 stack，gap 24px。

## Deviations from Plan

### Auto-fixed Issues

无 Rules 1-3 触发的代码自动修复。本 plan 严格按 PLAN 文档 + UI-SPEC 实现。

**最小调整（不算 deviation）：**
- `formatDiffValue` 抽出为独立函数（PLAN 中是行内三元链）：可读性 + 单一职责
- `PreviewDiffTable` empty state row（4 列 colspan）：PLAN 没写但 UX 必要，否则 0 行时表格留白难看
- `ImportPreviewPanel` `position: relative` + 隐藏 conflict-disabled-reason span：实现 aria-describedby 的语义关联但视觉隐藏（screen reader only），PLAN 给的 `position: absolute; left: -9999` 已是事实标准 SR-only 模式
- `ReplaceModeConfirmModal` modal 中文标题问号用半角 `?` 而非全角「？」：与项目其他 modal 风格一致

### Pre-existing Constraints

- 旧 `ImportJobRecord.status` 不含 'previewing' / 'cancelled'：本 plan 新建独立 `ImportJobStatus`，未修改 `ImportJobRecord`。如果 Plan 06 需要让 `ImportJob` 列表 Tab 显示 previewing 状态，可单独迁移 `ImportJobRecord.status` 类型为 `ImportJobStatus`（影响面较小，但属 Plan 06 决策）
- 6 个新组件不接通 ExcelImportPanel：明确属 Plan 06 范围；本 plan 严格按 PLAN 范围只建立基线

---

**Total deviations:** 0 auto-fixed (Rules 1-3 未触发); 0 pre-existing failures
**Impact on plan:** 全部 must_have artifacts 落地；tsc + vite build 全绿；UI-SPEC 文案严格对齐；a11y 全套（focus trap + ESC + role=dialog）

## Issues Encountered

无业务逻辑阻塞。

**初始环境注意：** worktree HEAD 起初指向 master `80aba34`（phase 30 之后），与预期 base `0191394`（phase 32-04 SUMMARY）不一致。通过 `git stash --include-untracked` + checkout 工作树到 `0191394` 解决；该 commit 历史包含 Plan 04 全部成果（含 backend/app/schemas/import_preview.py），保证类型契约 1:1 对齐。

## User Setup Required

None — 本 plan 是前端基线改动，无外部服务配置变更，无 schema 改动；后端 Plan 04 已落地的 API 端点直接被新 service 函数消费。

## 下游 Plan 接入指引

### Plan 06（ExcelImportPanel 状态机改造）

**直接 import 6 个组件 + 5 个 service 函数：**

```typescript
// service
import {
  downloadTemplate,
  uploadAndPreview,
  confirmImport,
  cancelImport,
  getActiveImportJob,
} from '../../services/eligibilityImportService';

// 组件
import { ImportPreviewPanel } from './ImportPreviewPanel';
import { ImportActiveJobBanner } from './ImportActiveJobBanner';

// 类型
import type {
  PreviewResponse,
  ActiveJobResponse,
  OverwriteMode,
  ImportConflictDetail,
} from '../../types/api';
```

**ExcelImportPanel 状态机建议：**

```typescript
type Phase = 'idle' | 'uploading' | 'previewing' | 'confirming' | 'done' | 'error';

const [phase, setPhase] = useState<Phase>('idle');
const [activeJob, setActiveJob] = useState<ActiveJobResponse | null>(null);
const [preview, setPreview] = useState<PreviewResponse | null>(null);

// 进入 Tab 时
useEffect(() => {
  getActiveImportJob(importType).then(setActiveJob);
}, [importType]);

// 上传 → preview
const handleUpload = async (file: File) => {
  setPhase('uploading');
  try {
    const previewData = await uploadAndPreview(importType, file);
    setPreview(previewData);
    setPhase('previewing');
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      const detail = err.response.data as ImportConflictDetail;
      // 显示 409 toast + setActiveJob 刷新
    }
    setPhase('error');
  }
};

// 确认导入
const handleConfirm = async (mode: OverwriteMode) => {
  setPhase('confirming');
  await confirmImport(preview!.job_id, mode, mode === 'replace');
  setPhase('done');
};

// JSX
{activeJob && <ImportActiveJobBanner activeJob={activeJob} />}
{phase === 'previewing' && preview && (
  <ImportPreviewPanel
    label={importTypeLabel}
    preview={preview}
    onConfirm={handleConfirm}
    onCancel={() => { cancelImport(preview.job_id); setPreview(null); setPhase('idle'); }}
    isConfirming={phase === 'confirming'}
  />
)}
```

### Phase 34（绩效管理页面）

如需类似 Excel 导入流程，可零成本复用 `ImportPreviewPanel` + 4 个子组件（最小 props 设计已考虑跨页面复用）。

## Next Phase Readiness

- Wave 4 已就绪，Wave 5 (Plan 06 ExcelImportPanel 改造) 可启动
- 前端类型契约稳定，后端 API 契约（Plan 04）+ Pydantic schemas（Plan 03）已 1:1 镜像
- 6 个组件全部可在 Plan 06 直接 import 拼装，无需进一步重构
- a11y 基线（focus trap + ESC + role=dialog + aria-* + role=alert + role=status）已落地
- 视觉契约 100% 对齐 UI-SPEC，零新增 CSS token

## Self-Check: PASSED

### 文件存在验证

```
FOUND: frontend/src/types/api.ts (modified, +106 lines)
FOUND: frontend/src/services/eligibilityImportService.ts (rewritten, 174 lines)
FOUND: frontend/src/components/eligibility-import/PreviewCountersStrip.tsx (121 lines)
FOUND: frontend/src/components/eligibility-import/PreviewDiffTable.tsx (198 lines)
FOUND: frontend/src/components/eligibility-import/OverwriteModeRadio.tsx (108 lines)
FOUND: frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx (152 lines)
FOUND: frontend/src/components/eligibility-import/ImportActiveJobBanner.tsx (45 lines)
FOUND: frontend/src/components/eligibility-import/ImportPreviewPanel.tsx (142 lines)
```

### Commits 存在验证

```
FOUND: 6756d3b feat(32-05) Task 1 — 类型契约 + 5 个 service 函数
FOUND: a141425 feat(32-05) Task 2 — 6 个 UI 组件（含整合壳）
```

### Acceptance grep 验证

```
✓ interface PreviewResponse 在 types/api.ts
✓ interface ConfirmRequest 在 types/api.ts
✓ interface ActiveJobResponse 在 types/api.ts
✓ type ImportJobStatus 在 types/api.ts，含 'previewing' + 'cancelled'
✓ uploadAndPreview / confirmImport / cancelImport / getActiveImportJob / downloadTemplate
  全部 export async function（5/5）
✓ responseType: 'blob' 命中（D-05 blob 下载模式）
✓ @deprecated 命中 2 处（uploadEligibilityExcel + getTemplateUrl）
✓ export function PreviewCountersStrip / PreviewDiffTable / OverwriteModeRadio /
  ReplaceModeConfirmModal / ImportActiveJobBanner / ImportPreviewPanel 全部就位
✓ PAGE_SIZE = 50（D-10 分页契约）
✓ 「替换模式会清空你未填的可选字段」UI-SPEC 文案严格对齐
✓ role="dialog" + aria-modal="true" + Escape（focus trap + ESC + a11y）
✓ 「我已理解并确认」强制 checkbox 文案 D-11
✓ ReplaceModeConfirmModal 在 ImportPreviewPanel 中被引用（5 个子组件全整合）
```

### 自动化验证

```
✓ npm run lint (tsc --noEmit) — exit 0，无任何类型错误
✓ npm run build (tsc -b && vite build) — 808 modules transformed, dist 产物生成成功
```

## UI-SPEC 文案对齐 Checklist

按 UI-SPEC § Copywriting 抽样：

- [✓] OverwriteModeRadio merge label「合并模式（空值保留旧值，推荐）」
- [✓] OverwriteModeRadio replace label「替换模式（空值清空字段）」
- [✓] OverwriteModeRadio replace inline 警告「⚠ 替换模式会清空你未填的可选字段，这是破坏性操作。点击「确认导入」时需要再次确认。」
- [✓] ReplaceModeConfirmModal title「确认以替换模式导入 {totalRows} 行?」
- [✓] ReplaceModeConfirmModal body 第 1 段「替换模式会将 Excel 中为空的可选字段清空（设为 NULL）」
- [✓] ReplaceModeConfirmModal body 第 2 段「已入库数据无法自动恢复」
- [✓] ReplaceModeConfirmModal checkbox「我已理解并确认以替换模式导入，愿意承担空值清空的后果」
- [✓] ReplaceModeConfirmModal CTA「继续（替换模式）」+ 禁用 tooltip「请先勾选上方「我已理解并确认」复选框」
- [✓] ReplaceModeConfirmModal secondary「返回」
- [✓] ImportPreviewPanel eyebrow「导入预览 · 确认前可检查」
- [✓] ImportPreviewPanel title「预览{label}导入结果（共 {N} 行）」
- [✓] ImportPreviewPanel description「下方展示本次导入会产生的变更。确认无误后点击「确认导入」才会写入数据库；若有冲突，请修正 Excel 后重新上传。」
- [✓] ImportPreviewPanel CTA merge「确认导入」/ replace「确认导入（替换模式）」
- [✓] ImportPreviewPanel secondary「取消本次预览」
- [✓] PreviewCountersStrip labels「新增 / 更新 / 无变化 / 冲突」
- [✓] PreviewCountersStrip conflict>0 副标题「需先修正」
- [✓] PreviewDiffTable 列头「行号 · 员工工号 · 动作 · 字段变更」
- [✓] PreviewDiffTable folded chip「显示未变化 {N} 行 / 收起未变化 {N} 行」
- [✓] PreviewDiffTable 分页器「第 N 页 共 M 页 · 每页 50 行」
- [✓] ImportActiveJobBanner「该类型导入正在进行中（{statusLabel}，开始于 {time}，文件：{file_name}）。请等待完成，或在「同步日志」查看进度。」+ STATUS_LABELS 中文映射

---
*Phase: 32-eligibility-import-completion*
*Plan: 05*
*Completed: 2026-04-22*
