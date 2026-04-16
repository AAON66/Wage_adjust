---
phase: 20
slug: employee-company
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-09
---

# Phase 20 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Alembic migration -> live employee schema | `company` 列若缺失、类型漂移或索引不一致，manual/import 路径会在运行时失配 | employee schema metadata |
| uploaded employee table -> ImportService upsert logic | 导入文件是否包含 `company` 列，直接决定是覆盖、清空还是保留旧值 | employee profile data (`company`) |
| admin / HR write path -> employee profile storage | 手动维护若不统一 trim/clear 语义，会和导入语义分裂 | employee profile data (`company`) |
| shared employee API payload -> multiple frontend consumers | `company` 进入共享 contract 后，任何页面都可能意外泄露该字段 | employee profile data (`company`) |
| admin form state -> employee PATCH/POST payload | 类型或回填不同步会导致 `company` 提交丢失、错误写入或被清空 | employee profile write payload |
| detail page rendering -> list page visibility requirement | 同一 employee contract 同时服务 detail 与 list，必须用渲染边界防止列表侧泄露 | employee profile display data |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-20-01 | Tampering | `alembic/versions/e55f2f84b5d1_add_company_to_employee.py` + `backend/app/models/employee.py` | mitigate | migration 与 ORM 同步更新；`backend/app/models/employee.py:23` 与 `alembic/versions/e55f2f84b5d1_add_company_to_employee.py:24-32` 对齐，且 `20-VERIFICATION.md` 记录 SQLite 升级 spot-check 通过 | closed |
| T-20-02 | Integrity | `backend/app/services/import_service.py` | mitigate | `backend/app/services/import_service.py:436-489` 使用 `has_company_column` 显式分支，只在列存在时更新已有员工；`20-VERIFICATION.md` 记录 clear/preserve 语义测试通过 | closed |
| T-20-03 | Repudiation | import template + API tests | mitigate | CSV/XLSX/API 三条路径都加入 `company` 断言；`backend/app/services/import_service.py:41,73` 对齐模板映射，`20-VERIFICATION.md` 记录相关测试通过 | closed |
| T-20-04 | Tampering | `backend/app/services/employee_service.py` | mitigate | `backend/app/services/employee_service.py:43,67-68` 在 manual create/update 路径统一 trim / clear；`20-VERIFICATION.md` 记录 CRUD 回归测试通过 | closed |
| T-20-05 | Information Disclosure | `frontend/src/pages/Employees.tsx` | mitigate | 列表页保持不渲染 `company`；`grep -n "employee.company\\|所属公司" frontend/src/pages/Employees.tsx` 无命中，`20-VERIFICATION.md` 记录静态 guardrail 通过 | closed |
| T-20-06 | Integrity | `frontend/src/components/employee/EmployeeArchiveManager.tsx` + `frontend/src/types/api.ts` | mitigate | `frontend/src/types/api.ts:77,94,107` 与 `frontend/src/components/employee/EmployeeArchiveManager.tsx:10,33,137-138` 同步增加 `company` 类型、回填与提交链路，避免表单状态漂移 | closed |
| T-20-07 | Spoofing / Misrepresentation | `frontend/src/pages/EvaluationDetail.tsx` | mitigate | 详情页直接消费 `fetchEmployee()` 返回的共享 payload；`frontend/src/pages/EvaluationDetail.tsx:630,2214` 仅渲染 `employee.company ?? '未设置'`，不拼接派生值 | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-09 | 7 | 7 | 0 | Codex (`/gsd-secure-phase`) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-09
