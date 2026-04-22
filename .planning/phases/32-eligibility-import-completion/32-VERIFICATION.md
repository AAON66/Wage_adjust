---
phase: 32-eligibility-import-completion
verified: 2026-04-22T02:30:00Z
status: passed
score: 5/5 ROADMAP Success Criteria + 5/5 IMPORT requirements 全满足
re_verification: null
followup:
  # 不阻塞 phase 完成的 minor a11y defects（已在 32-06-SUMMARY UAT 章节记录）
  - defect: "ReplaceModeConfirmModal focus trap querySelector 未过滤 [disabled]"
    file: frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx
    lines: 58-60
    severity: minor
    impact: "继续按钮 disabled 时 Tab 可能逃逸 modal（未触发用户实际损失）"
    fix_hint: "querySelectorAll 加 ':not([disabled])' 过滤"
  - defect: "ESC 关闭 modal 后焦点未恢复到原始触发按钮"
    file: frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx
    lines: 32-40
    severity: minor
    impact: "焦点落在 body，违反 WAI-ARIA dialog 模式"
    fix_hint: "useEffect open 钩子内保存 previouslyFocused = document.activeElement，关闭时 previouslyFocused?.focus()"
---

# Phase 32: 调薪资格导入功能补齐 — Verification Report

**Phase Goal:** HR 能通过调薪资格导入页面完整操作 hire_info / non_statutory_leave 等所有导入类型，模板下载返回真实 xlsx 文件，覆盖语义和并发行为符合行业默认

**Verified:** 2026-04-22T02:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths（5 ROADMAP Success Criteria + 8 PLAN frontmatter truths 合并）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC1) | HR 点击「下载模板」按钮，对所有调薪资格导入类型（含 hire_info / non_statutory_leave）都能拿到非空 .xlsx 文件，前端用 responseType: 'blob' 下载后 openpyxl 可成功读回 | ✓ VERIFIED | runtime spot-check：4 类模板各 5615-5661 bytes，A1='员工工号' format='@'；前端 downloadTemplate 用 axios responseType='blob' + URL.createObjectURL（eligibilityImportService.ts:81-94）；test_e2e_template_xlsx_downloadable parametrize 4 类全过；UAT-1 PASS |
| 2 (SC2) | HR 上传导入文件前能看到 Preview + diff（按业务键分 Insert/Update/No-change/冲突四类计数，字段级 diff 展示新旧值），点击「确认导入」才真正落库 | ✓ VERIFIED | PreviewResponse schema 含 counters / rows / file_sha256（import_preview.py）；build_preview 阶段不落库（import_service.py:1635）；confirm_import 才调 _dispatch_import 落库（import_service.py:1849）；UAT-2 截图：4 色 badge + grade:B→A + grade:(空)→S 字段级 diff |
| 3 (SC3) | HR 可显式勾选「覆盖模式」在 merge / replace 之间切换；AuditLog 记录本次导入的 overwrite_mode | ✓ VERIFIED | OverwriteModeRadio 组件 + ReplaceModeConfirmModal 二次确认；ConfirmRequest.overwrite_mode='merge'\|'replace'；confirm_import 写 AuditLog detail['overwrite_mode']（import_service.py:1909-1928）；用 AuditLog 真实字段 operator_id/target_type='import_job'/target_id |
| 4 (SC4) | 同一 import_type 的导入任务同时只能有一个 processing 状态；并发第二次提交时接口返回 409 冲突并提示「该类型导入正在进行中」 | ✓ VERIFIED | is_import_running per-import_type 分桶锁（import_service.py:1975）；_LOCKING_STATUSES = {previewing, processing}；preview/confirm 端点路由层 409 检查（eligibility_import.py:265-273）；UAT-4 截图 banner + HTTP 409 |
| 5 (SC5) | HR 导入同一批数据两次（模拟重复提交），系统按员工+周期维度覆盖更新，不会产生重复行 | ✓ VERIFIED | _BUSINESS_KEYS 4 类齐全（performance_grades=[employee_no,year]/salary_adj=[employee_no,date,type]/hire_info=[employee_no]/leave=[employee_no,year]）；uq_salary_adj_employee_date_type + uq_performance_employee_year + uq_leave_employee_year；test_e2e_perf_grades_idempotent + test_e2e_salary_adjustments_idempotent 通过 |
| 6 | ImportService.SUPPORTED_TYPES 含 6 类（含 hire_info/non_statutory_leave） | ✓ VERIFIED | runtime check: {certifications, employees, hire_info, non_statutory_leave, performance_grades, salary_adjustments}；REQUIRED_COLUMNS / COLUMN_ALIASES / TEMPLATE_TEXT_COLUMNS / COLUMN_LABELS 同步补齐 |
| 7 | ImportJob 模型有 overwrite_mode/actor_id/updated_at 三列，alembic 迁移 SQLite/PG upgrade-downgrade 通过 | ✓ VERIFIED | import_job.py:25-38 三字段（overwrite_mode String(16) NOT NULL default 'merge' / actor_id FK ondelete=SET NULL / updated_at server_default=now() onupdate=now()）；alembic 32_01_import_job_overwrite_mode 三阶段迁移 |
| 8 | SalaryAdjustmentRecord 增加 UniqueConstraint(employee_id, adjustment_date, adjustment_type) 与飞书同步业务键对齐 | ✓ VERIFIED | salary_adjustment_record.py:22-25 uq_salary_adj_employee_date_type；alembic 含 dedup + create_unique_constraint |
| 9 | 4 个 HTTP 端点完整实现：POST /excel/preview / POST /excel/{job_id}/confirm / POST /excel/{job_id}/cancel / GET /excel/active | ✓ VERIFIED | runtime check: paths registered in app.routes；require_roles('admin', 'hrbp') 全端点；_validate_upload_file (T-32-02/03)；deprecated POST /excel 保留 |
| 10 | APScheduler 定时任务 expire_stale_import_jobs 每 15 分钟执行 | ✓ VERIFIED | scheduler/import_scheduler.py：AsyncIOScheduler + IntervalTrigger(minutes=15) + run_expire_stale_jobs 独立 SessionLocal；main.py lifespan startup/shutdown 注册 |
| 11 | 前端 ImportFlowState 7 态机 + 6 个 React 组件 + 5 个 service 函数 + 11 个新 TS 类型 | ✓ VERIFIED | ExcelImportPanel.tsx:42-49 discriminated union 7 态；types/api.ts:1004-1108 11 个 Phase 32 类型；eligibilityImportService.ts 5 个新函数（downloadTemplate/uploadAndPreview/confirmImport/cancelImport/getActiveImportJob）；6 个组件全部 export function 且 tsc --noEmit exit 0 |
| 12 | AuditLog 写入用真实字段 operator_id / target_type / target_id（不是文档假设的 actor_id / resource_*） | ✓ VERIFIED | import_service.py:1912-1917 AuditLog(operator_id=actor_id, target_type='import_job', target_id=job.id, action='import_confirmed') 与 audit_log.py:20-23 真实模型字段对齐 |
| 13 | _staged_file_path 路径遍历双重防护（字符级 + Path.resolve+is_relative_to）+ sha256 文件 hash 校验 | ✓ VERIFIED | import_service.py:2078-2100 字符级拒 ../  /  \\ + resolve+is_relative_to；_save_staged_file 写入 sha256；_read_staged_file expected_sha256 校验，hash 不一致 raise ValueError |

**Score:** 13/13 truths VERIFIED （5 SC + 8 plan-level truths）

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/import_job.py` | overwrite_mode + actor_id + updated_at 字段 | ✓ VERIFIED | 39 lines, 3 字段全在；FK ondelete='SET NULL'；server_default 与 onupdate 配置正确 |
| `backend/app/models/salary_adjustment_record.py` | uq_salary_adj_employee_date_type | ✓ VERIFIED | 40 lines, __table_args__ 含 UniqueConstraint('employee_id', 'adjustment_date', 'adjustment_type') |
| `alembic/versions/32_01_import_job_overwrite_mode.py` | 三阶段迁移 + dedup + UC | ✓ VERIFIED | 112 lines, batch_alter add_column nullable → backfill 'merge' → alter NOT NULL；含 SQLite-safe dedup + alembic logger 写入 |
| `backend/app/services/import_service.py` | 6 类 + _BUSINESS_KEYS + 9 个新方法 | ✓ VERIFIED | 2139 lines；SUPPORTED_TYPES 6 类；_BUSINESS_KEYS 4 类；is_import_running / get_active_job / expire_stale_import_jobs / build_preview / confirm_import / cancel_import / _staged_file_path / _save_staged_file / _read_staged_file 9 个新方法存在 |
| `backend/app/schemas/import_preview.py` | 7 个 Pydantic v2 schemas | ✓ VERIFIED | 93 lines；FieldDiff / PreviewRow / PreviewCounters / PreviewResponse / ConfirmRequest / ConfirmResponse / ActiveJobResponse 全部 BaseModel + ConfigDict(extra='forbid') |
| `backend/app/api/v1/eligibility_import.py` | 4 个新端点 + _validate_upload_file + deprecated 旧端点 | ✓ VERIFIED | 413 lines；POST /excel/preview / POST /excel/{job_id}/confirm / POST /excel/{job_id}/cancel / GET /excel/active 全注册；require_roles('admin', 'hrbp') 全端点；_validate_upload_file 含 .xlsx/.xls 白名单 + 10MB 上限 + 空文件 400；旧 POST /excel 标 deprecated=True |
| `backend/app/scheduler/import_scheduler.py` | start/stop/run + AsyncIOScheduler + IntervalTrigger(15min) | ✓ VERIFIED | 63 lines；start_import_scheduler / stop_import_scheduler / run_expire_stale_jobs 全在；用 AsyncIOScheduler + IntervalTrigger(minutes=15)；run 用独立 SessionLocal + try/except 吞异常 |
| `backend/app/main.py` (modified) | lifespan 注册 import_scheduler | ✓ VERIFIED | grep 命中 line 121-122 startup + line 138-139 shutdown |
| `frontend/src/types/api.ts` | 11 个 Phase 32 类型 | ✓ VERIFIED | 1108 lines；EligibilityImportType / ImportJobStatus（含 'previewing'+'cancelled'）/ OverwriteMode / PreviewRowAction / FieldDiff / PreviewRow / PreviewCounters / PreviewResponse / ConfirmRequest / ConfirmResponse（status 用 Extract 窄化）/ ActiveJobResponse / ImportConflictDetail 全在 |
| `frontend/src/services/eligibilityImportService.ts` | 5 个新函数 + blob 下载 + deprecated 旧函数 | ✓ VERIFIED | 174 lines；downloadTemplate (responseType: 'blob' + URL.createObjectURL + `<a download>`)；uploadAndPreview (multipart + onUploadProgress + 120s timeout)；confirmImport (POST + ConfirmRequest body)；cancelImport (POST + 204 无返回)；getActiveImportJob；旧 uploadEligibilityExcel + getTemplateUrl 标 @deprecated |
| `frontend/src/components/eligibility-import/ExcelImportPanel.tsx` | 7 态状态机 + 整合 6 组件 | ✓ VERIFIED | 422 lines；ImportFlowState discriminated union (idle/uploading/previewing/confirming/done/cancelled/error)；import 5 service 函数 + ImportPreviewPanel + ImportActiveJobBanner；extractApiErrorMessage 兼容双 detail 结构 |
| `frontend/src/components/eligibility-import/ReplaceModeConfirmModal.tsx` | role=dialog + focus trap + ESC + 强制 checkbox | ✓ VERIFIED | 152 lines；role='dialog' + aria-modal + aria-labelledby + aria-describedby；handleKeyDown 实现 Tab 循环；ESC 监听器；checkbox + acknowledged state；每次 open 重置 + auto-focus checkbox |
| `frontend/src/components/eligibility-import/PreviewCountersStrip.tsx` | 4 色计数卡片 | ✓ VERIFIED | 121 lines（per SUMMARY） |
| `frontend/src/components/eligibility-import/PreviewDiffTable.tsx` | 分页 + no_change 折叠 + conflict 高亮 | ✓ VERIFIED | 198 lines（per SUMMARY） |
| `frontend/src/components/eligibility-import/OverwriteModeRadio.tsx` | merge/replace + replace inline 警告 | ✓ VERIFIED | 108 lines（per SUMMARY） |
| `frontend/src/components/eligibility-import/ImportActiveJobBanner.tsx` | active=true 时显示 banner | ✓ VERIFIED | 45 lines；UAT-4 截图证明实际渲染 |
| `frontend/src/components/eligibility-import/ImportPreviewPanel.tsx` | 整合 5 个子组件 + 受控状态 | ✓ VERIFIED | 142 lines（per SUMMARY） |
| `backend/tests/test_integration/test_import_e2e.py` | 4 类 × merge/replace × 重复幂等 + scheduler smoke | ✓ VERIFIED | 11/11 PASS（含 4 路 parametrize 模板下载 e2e + idempotent + replace + AuditLog 写入） |
| `.planning/phases/32-eligibility-import-completion/uat-screenshots/` | UAT 视觉证据 | ✓ VERIFIED | uat-2-preview-full.png（4 色 badge + 字段级 diff + Radio）、uat-4-tab-b-banner-409.png（橙黄色 ImportActiveJobBanner） |

**Artifact Score:** 19/19 VERIFIED

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `eligibility_import.py preview/confirm/cancel/active` | `ImportService.build_preview / confirm_import / cancel_import / get_active_job` | service 方法薄包装 | ✓ WIRED | runtime check: 5 paths in app.routes；router 调用 service.build_preview / confirm_import / cancel_import / get_active_job |
| `confirm_import` | `AuditLog with target_type='import_job'` | 写真实字段 operator_id/target_type/target_id | ✓ WIRED | import_service.py:1912-1928；test_confirm_import_writes_audit_log_with_real_fields 显式断言 |
| `import_service._import_*` | `_BUSINESS_KEYS` | 4 类硬编码已抽取到类常量 | ✓ WIRED | _BUSINESS_KEYS in {performance_grades, salary_adjustments, hire_info, non_statutory_leave}；_detect_in_file_conflicts + _build_row_diff 都从 _BUSINESS_KEYS 读 |
| `_save_staged_file` → `_read_staged_file` | sha256 校验 | preview 写入 result_summary.preview.file_sha256，confirm 透传校验 | ✓ WIRED | _save_staged_file 返回 sha256（line 2106）；_read_staged_file expected_sha256 参数（line 2112）；hash 不一致 raise ValueError |
| `import_scheduler.run_expire_stale_jobs` | `ImportService.expire_stale_import_jobs` | 独立 SessionLocal 调用 | ✓ WIRED | scheduler/import_scheduler.py:46-62 用 SessionLocal() + ImportService(db).expire_stale_import_jobs() |
| `main.py lifespan` | `import_scheduler.start_import_scheduler / stop_import_scheduler` | startup/shutdown 注册 | ✓ WIRED | main.py:121-122 startup + 138-139 shutdown，try/except 包裹防 lifespan 阻塞 |
| `ExcelImportPanel.tsx` | `eligibilityImportService 5 个新函数 + ImportPreviewPanel + ImportActiveJobBanner` | useState ImportFlowState + import 全部 | ✓ WIRED | imports lines 3-18 全部命中；UAT-2 + UAT-4 证明实际渲染 |
| `ReplaceModeConfirmModal` | confirm_replace=true to backend | 强制 checkbox + onConfirm | ✓ WIRED | acknowledged state 控制 disabled；勾选后 onConfirm 触发；前端 confirmImport(jobId, 'replace', true) → 后端 422 兜底验证 confirm_replace=True |
| `frontend/src/types/api.ts PreviewResponse` | `backend/app/schemas/import_preview.py PreviewResponse` | 1:1 镜像 Pydantic schema | ✓ WIRED | 11 个类型完整对齐 backend Pydantic schemas；ConfirmResponse.status 用 Extract<ImportJobStatus, 'completed'\|'partial'\|'failed'> 窄化 |

**Key Link Score:** 9/9 WIRED

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `ExcelImportPanel.tsx` flow.preview | `flow: ImportFlowState` discriminated union | `await uploadAndPreview(importType, file)` → axios POST /excel/preview → backend service.build_preview | ✓ Yes — Pydantic PreviewResponse 含真实 counters + rows | ✓ FLOWING |
| `ExcelImportPanel.tsx` activeJob | `activeJob: ActiveJobResponse` | `await getActiveImportJob(importType)` → GET /excel/active → svc.get_active_job(import_type) → DB 查 ImportJob WHERE status IN ('previewing','processing') | ✓ Yes — UAT-4 截图证明实际查到 active=true 后渲染 banner | ✓ FLOWING |
| `ImportPreviewPanel` 渲染 PreviewCountersStrip / PreviewDiffTable | `preview: PreviewResponse` props | 父 ExcelImportPanel 上一轮 uploadAndPreview 真实返回 | ✓ Yes — UAT-2 截图证明 4 色 badge 显示真实计数 + diff 表显示 grade:B→A | ✓ FLOWING |
| `confirm_import` ConfirmResponse | `inserted/updated/no_change/failed` 计数 | `_dispatch_import` 真实落库 + 派生 status | ✓ Yes — test_e2e_hire_info_merge 验证 DB 真实更新 + AuditLog 真实写入 | ✓ FLOWING |
| `expire_stale_import_jobs` returns dict | `{processing: N, previewing: M}` | DB 查 status='processing' AND created_at < cutoff 的 ImportJob 后 update status | ✓ Yes — test_run_expire_stale_jobs_uses_isolated_session 验证调用 + test_e2e_expire 系列覆盖双时限分支 | ✓ FLOWING |

**Data Flow Score:** 5/5 FLOWING（无 HOLLOW / DISCONNECTED）

---

### Behavioral Spot-Checks

| # | Behavior | Command | Result | Status |
|---|----------|---------|--------|--------|
| 1 | ImportService.SUPPORTED_TYPES 含 4 类资格 | `python -c "from backend.app.services.import_service import ImportService; ..."` | `True; {hire_info, non_statutory_leave, ...} <= SUPPORTED_TYPES` | ✓ PASS |
| 2 | _BUSINESS_KEYS 4 类完整定义 | `python -c "...print(ImportService._BUSINESS_KEYS)"` | hire_info=[employee_no], salary_adj=[employee_no, adjustment_date, adjustment_type], non_statutory_leave=[employee_no, year], perf_grades=[employee_no, year] | ✓ PASS |
| 3 | scheduler 模块暴露 4 核心符号 | `python -c "from backend.app.scheduler import import_scheduler; ..."` | start_import_scheduler / stop_import_scheduler / run_expire_stale_jobs / scheduler (AsyncIOScheduler) 全 True | ✓ PASS |
| 4 | 4 个新 API 端点已在 FastAPI 注册 | `python -c "from backend.app.main import app; ...print path in app.routes"` | preview/confirm/cancel/active/templates 全 True | ✓ PASS |
| 5 | 4 类资格模板都生成 ≥5615 字节真 xlsx + A1 文本格式 | `python -c "from backend.app.services.import_service import ImportService; svc.build_template_xlsx(itype)"` | performance_grades 5616, salary_adjustments 5661, hire_info 5632, non_statutory_leave 5656；A1='员工工号' format='@' 全部正确 | ✓ PASS |
| 6 | Phase 32 完整测试套件全 GREEN | `pytest backend/tests/test_integration/test_import_e2e.py + 14 个 service/api 测试文件` | 108 passed in 8.30s | ✓ PASS |
| 7 | 前端 TS 类型检查无错 | `cd frontend && npx tsc --noEmit` | exit 0，无任何类型错误 | ✓ PASS |

**Spot-Check Score:** 7/7 PASS

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| IMPORT-01 | 32-01 / 32-02 / 32-04 / 32-06 | ImportService.SUPPORTED_TYPES 补齐 hire_info/non_statutory_leave；REQUIRED_COLUMNS/COLUMN_ALIASES/_import_*/build_template_xlsx 同步补齐 | ✓ SATISFIED | runtime check: SUPPORTED_TYPES 含 6 类；2 个新 _import_* 方法实现；4 类模板都生成真 xlsx |
| IMPORT-02 | 32-04 / 32-05 / 32-06 | 模板下载返回非空 .xlsx，前端 axios 用 responseType: 'blob' | ✓ SATISFIED | 4 类各 5615+ 字节；downloadTemplate 用 responseType: 'blob' + URL.createObjectURL；UAT-1 PASS |
| IMPORT-05 | 32-01 / 32-02 / 32-04 / 32-05 / 32-06 | overwrite_mode='merge'\|'replace'，HR 必须显式勾选 replace 才生效；AuditLog 记录 overwrite_mode | ✓ SATISFIED | OverwriteModeRadio + ReplaceModeConfirmModal + confirm_replace=True 强制；AuditLog detail['overwrite_mode'] 写入；422 后端兜底拦截 |
| IMPORT-06 | 32-01 / 32-03 / 32-04 / 32-05 / 32-06 | 同 import_type 同时只能一个 processing；并发返回 409 | ✓ SATISFIED | is_import_running per-import_type 锁；preview/confirm 端点 409 拦截；UAT-4 截图 + 5 个并发场景 e2e |
| IMPORT-07 | 32-03 / 32-04 / 32-05 / 32-06 | 导入前强制 Preview + diff（4 色计数 + 字段级 diff），HR 必须显式确认 | ✓ SATISFIED | PreviewResponse + ImportPreviewPanel + 7 态机 confirm 步骤；test_e2e_*_conflict_detection 验证；UAT-2 截图 |

**Requirements Score:** 5/5 SATISFIED（无 ORPHANED；无 BLOCKED；REQUIREMENTS.md 中 Phase 32 映射的 5 个 IMPORT IDs 全在 PLAN frontmatter 中声明）

---

### Anti-Patterns Found

扫描了 Phase 32 触及的所有关键文件（import_service.py / eligibility_import.py / import_scheduler.py / 6 个前端组件 / 5 个 service 函数 / types/api.ts / 2 个 model 文件）：

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| ReplaceModeConfirmModal.tsx | 58-60 | focus trap querySelectorAll 未过滤 `:not([disabled])` | ⚠️ Warning (a11y minor) | 继续按钮 disabled 时 Tab 可能逃逸 modal；未阻塞核心功能（已在 followup 跟踪） |
| ReplaceModeConfirmModal.tsx | 32-40 | useEffect open 钩子无 previouslyFocused 保存 | ⚠️ Warning (a11y minor) | ESC 关闭后焦点落 body，违反 WAI-ARIA dialog 模式（已在 followup 跟踪） |

**未发现：**
- TODO/FIXME/PLACEHOLDER 占位（grep 0 命中相关代码）
- return null / return [] / return {} 空实现（spot-check 关键方法均含真实业务逻辑）
- Console.log only 实现（前端组件均含真实 JSX 渲染）
- Hardcoded empty data 渲染流向（PreviewResponse / ConfirmResponse / ActiveJobResponse 均由后端真实数据驱动）

**结论:** 无 blocker 级反模式；2 个 minor a11y warning 不阻塞 phase 完成（已在 SUMMARY UAT 章节明确标注 "minor"，由 SC 验收角度看 4/4 UAT 全 PASS）。

---

### Threat Model Mitigations Verification

| Threat | Mitigation | Status | Evidence |
|--------|-----------|--------|----------|
| T-32-01 (Tampering: 路径遍历) | _staged_file_path 双重防护（字符级 + Path.resolve+is_relative_to） | ✓ MITIGATED | import_service.py:2078-2100；test_import_staged_path_safety.py 7/7 PASS |
| T-32-02 (Spoofing: 文件类型) | _ALLOWED_XLSX_EXTENSIONS = {.xlsx, .xls} 白名单 | ✓ MITIGATED | eligibility_import.py:182；test_preview_endpoint_rejects_html / .exe |
| T-32-03 (DoS: 文件大小) | _MAX_UPLOAD_SIZE_BYTES = 10MB 上限 | ✓ MITIGATED | eligibility_import.py:189；test_preview_rejects_oversized_file |
| T-32-04 (Repudiation: 操作来源) | confirm 端点 actor_id 来自 current_user.id | ✓ MITIGATED | eligibility_import.py:345；写入 AuditLog.operator_id 与 ImportJob.actor_id |
| T-32-05 (并发竞争) | DB 层 is_import_running per-import_type 锁 | ✓ MITIGATED | import_service.py:1975-1986；5 个并发场景 e2e |
| T-32-06 (审计完整性) | AuditLog 强制 operator_id + overwrite_mode in detail | ✓ MITIGATED | import_service.py:1912-1928；test_confirm_import_writes_audit_log_with_real_fields |
| T-32-07 (Authorization: replace 滥用) | replace 模式仅 admin/hrbp 角色（require_roles 全端点） | ✓ MITIGATED | eligibility_import.py:232/293/369/387 共 4 处 require_roles('admin', 'hrbp')；test_employee_role_returns_403 |
| T-32-14 (sha256 文件 hash 校验) | _save_staged_file 写 sha256 / _read_staged_file 校验 | ✓ MITIGATED | import_service.py:2102-2133；test_confirm_hash_mismatch_raises |
| T-32-15 (Replace 二次确认绕过) | ConfirmRequest.confirm_replace=True 强制；前端 modal + 后端 422 双重防护 | ✓ MITIGATED | ReplaceModeConfirmModal.tsx + import_service.py confirm_import；测试覆盖 422 分支 |

**Threat Mitigation Score:** 9/9 MITIGATED

---

### 18 D-XX Decisions Implementation

| Decision | Description | Status | Evidence |
|----------|-------------|--------|----------|
| D-01 | SUPPORTED_TYPES 6 类 | ✓ | runtime check |
| D-02 | hire_info 模板字段对齐飞书同步 | ✓ | REQUIRED_COLUMNS/COLUMN_ALIASES.hire_info（含「末次调薪日期」+「历史调薪日期」兼容） |
| D-03 | non_statutory_leave 模板字段对齐 NonStatutoryLeave 模型 | ✓ | COLUMN_ALIASES.non_statutory_leave（员工工号/年度/假期天数/假期类型） |
| D-04 | build_template_xlsx 复用 openpyxl + 105 行预填 | ✓ | TEMPLATE_TEXT_PREFILL_ROWS=105 |
| D-05 | 前端 blob 下载（axios responseType:'blob'） | ✓ | downloadTemplate(eligibilityImportService.ts:81-94) |
| D-06 | 两阶段提交文件暂存方案（preview→confirm） | ✓ | build_preview + confirm_import + _staged_file_path |
| D-07 | PreviewResponse 含 counters/rows/file_sha256/preview_expires_at | ✓ | import_preview.py PreviewResponse |
| D-08 | Diff 行级 + 字段级（4 色 badge + old/new） | ✓ | PreviewRow.fields: dict[str, FieldDiff]；UAT-2 截图 |
| D-09 | 冲突检测在 preview 阶段同文件业务键 | ✓ | _detect_in_file_conflicts |
| D-10 | 大批量分页（每页 50 行） | ✓ | PAGE_SIZE=50 in PreviewDiffTable |
| D-11 | Radio + 二次确认 modal + 强制 checkbox | ✓ | OverwriteModeRadio + ReplaceModeConfirmModal |
| D-12 | overwrite_mode 语义（merge/replace） | ✓ | confirm_import overwrite_mode 透传到 _dispatch_import |
| D-13 | AuditLog action='import_confirmed' + detail 含 overwrite_mode（用真实字段） | ✓ | confirm_import line 1912-1928 (operator_id/target_type/target_id) |
| D-14 | 4 类业务键三元组对齐飞书 | ✓ | _BUSINESS_KEYS 类常量；uq_salary_adj_employee_date_type 模型 + alembic |
| D-15 | PerformanceRecord 已有 UC 不重复加 | ✓ | 32-01 SUMMARY 确认 uq_performance_employee_year 已存在 |
| D-16 | per-import_type 分桶锁（_LOCKING_STATUSES 含 previewing+processing） | ✓ | is_import_running |
| D-17 | APScheduler IntervalTrigger 每 15 分钟 | ✓ | import_scheduler.py（不是 Celery Beat） |
| D-18 | 前端进入 Tab 即查 active job + 禁用按钮 | ✓ | ExcelImportPanel useEffect getActiveImportJob + ImportActiveJobBanner |

**Decisions Score:** 18/18 IMPLEMENTED

---

### 5 Open Questions Resolution

| OQ | Resolution | Implemented in Plan | Code Evidence |
|----|-----------|---------------------|---------------|
| OQ1 | salary_adjustments 业务键 = (employee_no, adjustment_date, adjustment_type) | 32-01 + 32-02 | uq_salary_adj_employee_date_type + _BUSINESS_KEYS |
| OQ2 | 选 APScheduler 而非 Celery Beat | 32-06 | import_scheduler.py 用 AsyncIOScheduler + IntervalTrigger |
| OQ3 | confirm 端点同步执行（不走 Celery） | 32-03 + 32-04 | confirm_import 同步调 _dispatch_import；POST /confirm 直接返回 ConfirmResponse |
| OQ4 | 旧 POST /excel 标 deprecated 保留兼容 | 32-04 | @router.post('/excel', deprecated=True) |
| OQ5 | sha256 文件 hash 校验 | 32-03 | _save_staged_file + _read_staged_file expected_sha256 |

**OQ Score:** 5/5 RESOLVED

---

### Human Verification Required

无新增人工验证需求。Phase 32 已通过 Playwright + 后端 API 自动化完成 4/4 UAT（详见 32-06-SUMMARY.md「UAT 自动化执行结果」章节，含 2 张截图证据）。

剩余 2 个 minor a11y defect（focus trap 未过滤 disabled / ESC 后焦点未恢复）已在本报告 frontmatter `followup` 中记录，作为后续 phase 改进项，不阻塞 Phase 32 验收。

---

### Gaps Summary

**无 gap。** Phase 32 全部 13 个 must-have truths 验证通过：

- 5 个 ROADMAP Success Criteria（SC1-SC5）全部成立
- 8 个 PLAN frontmatter truths（涵盖 schema / service / api / scheduler / 前端 5 件套）全部成立
- 5 个 IMPORT requirements 全部满足（IMPORT-01/02/05/06/07）
- 9 个威胁模型 mitigations 全部落地（含 T-32-01 至 T-32-07 + T-32-14/15）
- 18 个 D-XX 决策全部实施
- 5 个 RESEARCH Open Questions 全部 RESOLVED
- 21 个 commit 全部存在 git 历史
- 108 个 Phase 32 测试 PASS（0 regression；pre-existing 26 个失败已在 deferred-items.md 跟踪，与本期改动无交集）
- 4/4 UAT PASS（含 2 张截图视觉证据）
- 前端 tsc --noEmit exit 0
- 后端运行时验证：SUPPORTED_TYPES / _BUSINESS_KEYS / scheduler 符号 / API 端点注册 / 4 类模板真 xlsx + A1 文本格式 全部正确

**Followup（不阻塞 phase 完成，建议后续 phase 修复）：**
1. ReplaceModeConfirmModal focus trap querySelectorAll 加 `:not([disabled])` 过滤
2. ReplaceModeConfirmModal ESC 关闭后恢复焦点到原始触发按钮（保存 previouslyFocused = document.activeElement）

---

*Verified: 2026-04-22T02:30:00Z*
*Verifier: Claude (gsd-verifier)*
