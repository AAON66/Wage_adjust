---
phase: 27-oauth2
plan: 01
subsystem: frontend
tags: [feishu, oauth2, types, services, error-handling]
dependency_graph:
  requires:
    - Phase 26 backend OAuth2 endpoints (/auth/feishu/authorize, /auth/feishu/callback)
    - backend/app/schemas/user.py UserRead.feishu_open_id
    - backend/app/main.py exception_handler (HTTPException -> {error, message})
  provides:
    - frontend FeishuAuthorizeResponse / FeishuCallbackPayload contract
    - UserProfile.feishu_open_id field exposed to React state
    - authorizeFeishu() / feishuCallback(code, state) service functions
    - resolveFeishuError(source, payload) with 8-category Chinese copy
  affects:
    - Plan 27-02 (useAuth.loginWithFeishu + FeishuCallbackPage) consumes all three files
    - Plan 27-03 (FeishuLoginPanel QR widget) consumes authorizeFeishu + resolveFeishuError
tech_stack:
  added: []
  patterns:
    - axios.isAxiosError discrimination for error classification
    - response.data.message primary / response.data.detail fallback (App.tsx:51 pattern)
    - Frontend-static Chinese copy (never render backend strings verbatim) — XSS mitigation
key_files:
  created:
    - frontend/src/utils/feishuErrors.ts
  modified:
    - frontend/src/types/api.ts
    - frontend/src/services/auth.ts
decisions:
  - Prefer response.data.message over response.data.detail (backend main.py exception_handler改写格式优先)
  - 错误文案使用前端静态映射表 COPY，不使用后端原文作为 UI 文案 (T-27-01 XSS 防御)
  - SDK 错误源专用 classifier，保留扩展空间给 Plan 03 postMessage 路径
metrics:
  duration: ~12 minutes
  completed_date: 2026-04-19
  tasks_total: 3
  tasks_completed: 3
requirements:
  - FUI-04
---

# Phase 27 Plan 01: 类型契约、服务封装与错误映射基础设施 Summary

**One-liner:** 为飞书 OAuth2 前端接入建立 types 契约、services 封装与分类错误映射，下游 Plan 02/03 可无缝消费。

## Outcome

为 Phase 27 下游 Plan 提供 3 个基础设施文件：

1. `frontend/src/types/api.ts` — `UserProfile.feishu_open_id: string | null` 字段 + `FeishuAuthorizeResponse` / `FeishuCallbackPayload` 两个 interface 导出；与 Phase 26 后端 `UserRead.feishu_open_id: Optional[str]` 完全对齐。
2. `frontend/src/services/auth.ts` — 新增 `authorizeFeishu()` 与 `feishuCallback(code, state)` 两个 async 函数，命中 `/auth/feishu/authorize` 与 `/auth/feishu/callback` 两个后端端点；保留项目既有 async + await + return response.data 风格，无 try/catch、无 Authorization 头手动设置。
3. `frontend/src/utils/feishuErrors.ts` — 新文件，导出 `resolveFeishuError(source, payload)` 映射函数与 `FeishuErrorCode` 类型；8 类错误码覆盖 backend（503/403/400 细分）+ SDK（sdk_load_failed）+ 网络 + 未知。

全部为纯类型 + 纯函数，无 React / DOM / 副作用。`cd frontend && npm run lint` 与 `cd frontend && npm run build` 双通过。

## Tasks Completed

| Task | Name                                          | Commit   | Files                                 |
| ---- | --------------------------------------------- | -------- | ------------------------------------- |
| 1    | 添加飞书前端类型定义                          | b8b3ec5  | frontend/src/types/api.ts             |
| 2    | 实现 feishuErrors.ts 错误映射工具             | e30e1fc  | frontend/src/utils/feishuErrors.ts    |
| 3    | 新增 authorizeFeishu + feishuCallback 服务函数 | 5d879ef  | frontend/src/services/auth.ts         |

## Key Changes

### frontend/src/types/api.ts (diff 摘要)

- `UserProfile` 在 `employee_no: string | null;` 之后插入 `feishu_open_id: string | null;`（与后端 UserRead 对齐）。
- 在 `AuthResponse` 与 `LoginPayload` 之间新增 `FeishuAuthorizeResponse { authorize_url, state }` 与 `FeishuCallbackPayload { code, state }` 两个 interface，均使用 `export interface` 风格，与现有类型归档相邻。
- 未改动任何其他已有字段（git diff 仅影响上述三处）。

### frontend/src/utils/feishuErrors.ts (新文件)

- 定义 `FeishuErrorCode` 联合类型（8 类）与 `FeishuError` interface。
- 定义 `COPY: Record<FeishuErrorCode, string>` 中文文案映射（纯前端静态定义）。
- `extractDetail(data)` 优先读 `data.message`，回退 `data.detail`（兼容 main.py exception_handler 改写后的 `{error, message}` 与 FastAPI 默认 `{detail}` 两种 shape）。
- `classifyBackend(err)` 按 `axios.isAxiosError` → `err.response` 存在性 → `status` → `detail` 关键字（`state` / `工号` / `授权码`）做分类。
- `classifySdk(payload)` 仅识别 `new Error('sdk_load_failed')`；其它 SDK 运行时异常归 `unknown_error`。
- `resolveFeishuError(source, payload)` 按 source 分派并返回 `{ code, message: COPY[code] }`。
- 不使用 `innerHTML` / `dangerouslySetInnerHTML`（T-27-01）；不 `console.log` / `console.error` payload（T-27-03）。

### frontend/src/services/auth.ts (diff 摘要)

- 第 2 行 type import 列表新增 `FeishuAuthorizeResponse`、`FeishuCallbackPayload`（字母序插入 `ChangePasswordPayload` 之后、`LoginPayload` 之前）。
- 文件末尾追加 `authorizeFeishu()` 与 `feishuCallback(code, state)` 两个 async 函数；未修改任何既有函数。

## Deviations from Plan

None - plan 按照原定设计逐字执行，所有 Task action 中描述的代码片段均已原样落地。

## A4 / A5 假设验证结论（复述）

- **A4** — `backend/app/main.py:132-142` 存在 `@app.exception_handler(HTTPException)` 自定义 handler，将 HTTPException.detail 改写为 `{error, message}` 格式。前端 `extractDetail` 因此采用 `message` 为主路径，`detail` 为回退路径（兼容 FastAPI 默认格式）。本 Plan 未发现实际代码与该假设不一致。
- **A5** — `.env.example:61` 行 `FEISHU_REDIRECT_URI=http://localhost:5174/auth/feishu/callback` 指向前端 Vite dev server 路由，与 Phase 26 后端契约 + Plan 27-02 路由规划一致。本 Plan 未触达 `.env` 实际部署配置；若执行 Plan 02 / 03 时发现部署环境 redirect_uri 指向后端端口，应 BLOCK 并汇报。

## Unit Test Strategy

- 前端项目 `package.json` 当前无 vitest / jest 配置（`scripts` 仅 `dev / build / lint / preview`），Plan 01 不跑单元测试。
- `feishuErrors.ts` 的 8 类分类与 COPY 表由 Plan 02 / Plan 03 在 `FeishuCallbackPage` / `FeishuLoginPanel` 手动验证路径（模拟各状态码 + 网络错误）接棒覆盖。
- `authorizeFeishu()` / `feishuCallback(code, state)` 的 HTTP 契约由 Plan 02 端到端验证（useAuth.loginWithFeishu + 跳转回角色首页）。

## Verification

- `cd frontend && npm run lint` 退出码 0（tsc --noEmit 无错误）。
- `cd frontend && npm run build` 退出码 0（tsc -b + vite build 双通过，产物 `dist/index.html` 与 `dist/assets/*` 生成）。
- grep 逐条核对所有 acceptance_criteria：
  - `feishu_open_id: string | null` ✓
  - `export interface FeishuAuthorizeResponse` ✓
  - `export interface FeishuCallbackPayload` ✓
  - `export function resolveFeishuError` ✓
  - `export type FeishuErrorCode` ✓
  - 8 类错误码合计 28 处关键字出现（union 声明 + COPY 映射 + 分类返回共 28 处） ✓
  - `maybe.message` 与 `maybe.detail` 两种 fallback ✓
  - `export async function authorizeFeishu` / `feishuCallback` ✓
  - `/auth/feishu/authorize` / `/auth/feishu/callback` 两条路径 ✓

## Threat Mitigations Applied

- **T-27-01** (XSS via error message)：`feishuErrors.ts` 返回的 `message` 完全来自前端静态 `COPY` 映射表，后端 `detail` 原文仅参与字符串 `includes` 关键字分类，**从未**作为 UI 文案输出。下游 Plan 02 / 03 应通过 React 文本节点直接渲染 `{message}`（React 默认 HTML escape），禁止 `innerHTML` / `dangerouslySetInnerHTML`。
- **T-27-03** (Information Disclosure via code/state 泄漏)：`feishuErrors.ts` 与 `auth.ts` 均**不**调用 `console.log` / `console.error`；不把 `error.response.data` 写入任何本地日志或 telemetry。Plan 02 / 03 应继承此约束。

## Threat Flags

None — 本 Plan 未引入新的网络端点、鉴权路径、文件访问模式或 schema 变更；三文件均为前端纯类型/纯函数基础设施。

## Known Stubs

None — 所有导出均为可直接消费的完整实现；`resolveFeishuError` 的 8 类分类覆盖已在 Plan 02 / 03 的错误场景矩阵内，没有 UI 层或服务层 placeholder。

## Self-Check

- [x] frontend/src/types/api.ts exists (FOUND, modified, git diff clean except 3 insertions)
- [x] frontend/src/utils/feishuErrors.ts exists (FOUND, new file, 69 lines)
- [x] frontend/src/services/auth.ts exists (FOUND, modified, 12 insertions / 1 deletion in import line)
- [x] Commit b8b3ec5 exists in log (FOUND)
- [x] Commit e30e1fc exists in log (FOUND)
- [x] Commit 5d879ef exists in log (FOUND)
- [x] `cd frontend && npm run lint` exit code 0 (PASSED)
- [x] `cd frontend && npm run build` exit code 0 (PASSED)

## Self-Check: PASSED
