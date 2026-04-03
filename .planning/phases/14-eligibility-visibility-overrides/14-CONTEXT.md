# Phase 14: Eligibility Visibility & Overrides - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

调薪资格校验结果仅对 HR/主管/管理端可见，HR 可批量查看资格状态列表（多维度筛选 + Excel 导出），不合格员工可由主管/HRBP 提交特殊申请经两级审批后覆盖资格判定。

</domain>

<decisions>
## Implementation Decisions

### 资格列表页面设计
- **D-01:** 多维度筛选——支持按部门、资格状态（合格/不合格/待定/全部）、具体规则（入职时长/绩效/调薪间隔/假期）、岗位族、职级筛选
- **D-02:** 支持 Excel 导出——将筛选结果导出为 Excel 文件

### 特殊申请审批流程
- **D-03:** 主管/HRBP 可为下属不合格员工发起特殊申请
- **D-04:** 两级审批链——HRBP 审批 → Admin 审批，两级都通过才生效
- **D-05:** 申请字段为"理由（文本）+ 选择要覆盖的具体规则"，不需要附件
- **D-06:** 审批通过后覆盖资格判定——被覆盖的规则在资格结果中显示为"已覆盖"状态

### 权限隔离
- **D-07:** 后端不返回 + 前端不显示双重保障——employee 角色请求资格 API 返回 403，前端菜单和路由同时隐藏
- **D-08:** 主管看本部门员工的资格状态，复用现有 AccessScopeService 进行范围过滤
- **D-09:** HR/Admin 可查看全公司员工资格状态

### 前端页面入口
- **D-10:** 资格页面放在"运营管理"菜单分组下，与员工评估、审批中心并列
- **D-11:** 单页面双 Tab 结构——"调薪资格"页面含两个 Tab：资格列表 + 特殊申请列表
- **D-12:** employee 角色的菜单中不显示此页面

### Claude's Discretion
- 特殊申请的数据模型设计（新表 vs 复用 ApprovalRecord）
- 资格列表的分页策略和默认排序
- Excel 导出的具体格式和字段
- 前端组件的具体拆分方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 资格引擎（Phase 13 产出）
- `backend/app/engines/eligibility_engine.py` — EligibilityEngine, RuleResult, EligibilityResult 数据结构
- `backend/app/services/eligibility_service.py` — EligibilityService.check_employee() 方法签名
- `backend/app/api/v1/eligibility.py` — 现有资格 API 端点
- `backend/app/schemas/eligibility.py` — 现有 Pydantic schemas

### 权限控制
- `backend/app/services/access_scope_service.py` — AccessScopeService 范围过滤模式
- `backend/app/dependencies.py` — require_roles() 工厂函数

### 审批流程
- `backend/app/models/approval.py` — 现有 ApprovalRecord 模型（绑定 SalaryRecommendation）
- `backend/app/services/approval_service.py` — 现有审批服务模式

### 前端菜单
- `frontend/src/utils/roleAccess.ts` — MenuGroup 和角色菜单配置（Phase 11 产出）
- `frontend/src/components/layout/AppShell.tsx` — 侧边栏渲染

### 需求文档
- `.planning/REQUIREMENTS.md` — ELIG-05, ELIG-06, ELIG-07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AccessScopeService`: 已有部门范围过滤，主管看本部门逻辑可直接复用
- `EligibilityService.check_employee()`: 单员工资格检查已实现，批量查询需新增方法
- `roleAccess.ts MenuGroup`: Phase 11 分组菜单结构，新页面只需加到运营管理组
- `ApprovalRecord`: 现有审批模型绑定 SalaryRecommendation，特殊申请可能需要独立模型

### Established Patterns
- API 权限通过 `require_roles()` + `AccessScopeService.ensure_*_access()` 组合控制
- 前端路由通过 `App.tsx` 和 `roleAccess.ts` 双重控制角色可见性
- 审批流使用 step_name + step_order + generation 多步审批

### Integration Points
- 资格列表 API 需要批量调用 EligibilityEngine（注意 N+1 查询风险）
- 特殊申请审批需要新的审批类型或独立模型
- 前端新页面需要注册路由和菜单项

</code_context>

<specifics>
## Specific Ideas

- 批量资格查询应做查询优化（预加载关联数据），避免 N+1
- 特殊申请覆盖后，资格结果中对应规则应显示"已覆盖（特殊审批）"而非原始状态
- 两级审批中，第一级拒绝则直接终止，无需第二级

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 14-eligibility-visibility-overrides*
*Context gathered: 2026-04-03*
