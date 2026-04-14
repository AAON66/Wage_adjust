---
status: awaiting_human_verify
trigger: "员工评估列表页面的筛选功能不正常 - IME冲突 + 需要重新设计筛选UI"
created: 2026-04-12T00:00:00Z
updated: 2026-04-12T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Employees.tsx 的筛选输入框在每次 onChange 时直接更新 URL searchParams，触发 API 调用，导致 IME 中文输入被中断
test: 已确认代码逻辑
expecting: N/A - root cause confirmed
next_action: 等待用户验证修复效果

## Symptoms

expected: 筛选条件用下拉勾选（如部门、AI等级、状态），另有搜索框可按员工工号或姓名搜索。筛选后列表实时过滤。
actual: 当前输入框在中文输入法输入时会触发其他事件（如搜索/刷新），导致中文输入中断无法正常输入。筛选功能需要重新设计为下拉选项勾选 + 工号/姓名搜索框的模式。
errors: 中文输入法（IME）冲突，composing 过程中触发了 onChange 或其他事件处理
reproduction: 在评估列表页面，用中文输入法在筛选输入框中输入，输入过程会被中断
started: 一直存在的问题

## Eliminated

## Evidence

- timestamp: 2026-04-12T00:01:00Z
  checked: frontend/src/pages/Employees.tsx (lines 112-115)
  found: 三个筛选输入框都是 <input> 元素，onChange 直接调用 updateFilter -> setSearchParams -> 触发 useEffect -> API 调用。每个按键都会触发，IME composing 期间也不例外。
  implication: 这是 IME 中断的直接原因

- timestamp: 2026-04-12T00:02:00Z
  checked: backend/app/api/v1/employees.py (line 38)
  found: 后端已支持 keyword 查询参数，但前端 EmployeeQuery 接口和 Employees.tsx 都没有使用它
  implication: 可以直接利用后端已有的 keyword 参数实现搜索

- timestamp: 2026-04-12T00:03:00Z
  checked: frontend/src/services/userAdminService.ts
  found: fetchDepartments() 已存在，可直接用于获取部门下拉列表
  implication: 无需新建 API，直接复用

- timestamp: 2026-04-12T00:04:00Z
  checked: frontend/src/components/evaluation/StatusIndicator.tsx
  found: 员工状态只有 active/inactive 两个值
  implication: 状态筛选可用固定下拉选项

## Resolution

root_cause: Employees.tsx 的筛选输入框在每次 onChange 时直接通过 setSearchParams 更新 URL 参数，立即触发 useEffect 和 API 调用。中文 IME composing 过程中每个按键都会触发 onChange，导致输入被中断。此外，部门/状态/岗位族筛选使用纯文本输入而非下拉选择，用户体验差。
fix: 1) 部门筛选改为下拉（从 API 获取部门列表）2) 状态筛选改为下拉（active/inactive 固定选项）3) 岗位族筛选改为下拉（从员工数据提取 distinct 值）4) 新增关键词搜索框，支持按工号/姓名搜索，使用 useRef composing 守卫 + debounce 防止 IME 冲突 5) EmployeeQuery 接口添加 keyword 字段
verification: TypeScript 编译通过（tsc --noEmit 无错误）。部门/岗位族/状态改为下拉选择不再涉及 IME 输入。搜索框使用 compositionStart/End 守卫 + 400ms debounce，IME composing 期间不触发搜索。后端 keyword 参数已验证支持 name/employee_no ILIKE 搜索。
files_changed: [frontend/src/pages/Employees.tsx, frontend/src/types/api.ts]
