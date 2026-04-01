# Phase 12: Account-Employee Binding — Context

**Status:** Ready for planning (gathered 2026-04-01)

---

## Phase Boundary

**In scope:**
- 管理员在用户管理页手动绑定/解绑用户与员工
- 员工在个人设置页通过身份证号自助绑定
- 绑定冲突检测和阻止
- 解绑后强制重新登录
- 未绑定用户顶部警告条引导

**Out of scope:**
- 批量绑定
- SSO/LDAP 集成
- 新建用户管理页面（在现有页面内联）

---

## Implementation Decisions

### D-01: 管理员绑定 UI — 用户管理页内联

- 在现有用户列表表格新增「绑定状态」列，显示已绑定的员工姓名+工号，未绑定显示「未绑定」
- 点击「绑定」打开弹窗，搜索并选择员工（按姓名/工号搜索）
- 点击「解绑」弹出确认对话框后执行解绑
- 不新建独立页面

### D-02: 员工自助绑定 — 三步确认流程

1. 在个人设置页（账号设置）显示绑定状态区域
2. 未绑定时：输入身份证号 → 调用后端搜索匹配的员工
3. 匹配成功：显示员工姓名+工号供用户确认 → 点击「确认绑定」完成
4. 匹配失败或已被占用：提示对应错误信息

### D-03: 解绑后处理 — 强制重新登录

- 管理员解绑某用户后，清除该用户的 refresh token（后端新增 token 黑名单或版本号机制）
- 该用户下次请求时 access token 过期后无法刷新，被迫重新登录
- 重新登录后 JWT claims 中 employee_id 为空，权限自动收窄
- 自助解绑同理

### D-04: 未绑定引导 — 顶部黄色警告条

- 登录后如果 user.employee_id 为空，在 AppShell 顶部显示黄色警告条
- 文案：「您尚未绑定员工信息，部分功能受限。[立即绑定]」
- 点击跳转到个人设置页的绑定区域
- 已绑定用户不显示警告条
- 管理员角色不显示（admin 可能不需要绑定员工）

### D-05: 绑定冲突提示

- 当目标员工已被其他账号绑定时：提示「该员工已绑定到账号 xxx@xxx.com，请联系管理员处理」
- 当用户已绑定其他员工时（管理员操作）：先解绑旧员工再绑定新员工，或提示确认

### D-06: API 端点设计

- `POST /api/v1/users/{user_id}/bind` — 管理员绑定（body: {employee_id}）
- `DELETE /api/v1/users/{user_id}/bind` — 管理员解绑
- `POST /api/v1/auth/self-bind` — 员工自助绑定（body: {id_card_no}）
- `GET /api/v1/auth/self-bind/preview` — 员工预览匹配结果（query: id_card_no）

---

## Canonical References

| File | Purpose |
|------|---------|
| `backend/app/services/identity_binding_service.py` | 已有绑定逻辑（auto_bind, 冲突检测, 身份证匹配） |
| `backend/app/models/user.py` | User 模型，已有 employee_id FK 和 id_card_no |
| `backend/app/api/v1/users.py` | 现有用户管理 API |
| `backend/app/api/v1/auth.py` | 认证 API |
| `backend/app/core/security.py` | JWT 生成/验证 |
| `frontend/src/pages/UserAdmin.tsx` | 用户管理页面（绑定列 + 操作按钮目标） |
| `frontend/src/pages/Settings.tsx` | 账号设置页面（自助绑定目标） |
| `frontend/src/components/layout/AppShell.tsx` | 顶部警告条目标 |

## Reusable Assets

- `IdentityBindingService` — auto_bind_user_and_employee 可直接复用
- `search_employee_for_user_by_identity` — 自助绑定预览可复用
- 冲突检测逻辑（已有 ValueError raise）

## Claude's Discretion

- 员工搜索弹窗的具体交互（搜索框样式、结果列表样式）
- 警告条的具体 CSS 样式
- Token 失效机制的具体实现方式（黑名单 vs token version 字段）
- 解绑确认对话框的文案
