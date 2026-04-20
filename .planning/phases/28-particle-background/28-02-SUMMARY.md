---
phase: 28-particle-background
plan: 02
subsystem: ui
tags: [react, canvas, login, integration, z-index, pointer-events, uat-pending]

# Dependency graph
requires:
  - phase: 28
    plan: 01
    provides: frontend/src/components/common/ParticleBackground.tsx (零 props Canvas 粒子背景组件)
provides:
  - Login.tsx 挂载 ParticleBackground 的集成层（<main> z-index:1）
  - Phase 28 端到端交付（待 UAT 验收）
affects:
  - 29 (登录页重设计整合 — 本集成验证了 z-index:0/1 分层方案可用)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fragment 包装 return 以让纯装饰层组件与语义 <main> 同级，保证 z-index:0 Canvas 与 z-index:1 主内容共存"
    - "<main> 显式 position: relative + zIndex: 1 激活层叠上下文，防止 pointer-events:none Canvas 在视觉层影响主内容"

key-files:
  created:
    - .planning/phases/28-particle-background/28-02-SUMMARY.md (partial — awaits UAT)
  modified:
    - frontend/src/pages/Login.tsx (+44 / -40)

key-decisions:
  - "沿用 D-03：Canvas z-index:0 + pointer-events:none；<main> z-index:1 + position:relative"
  - "沿用 D-02：ParticleBackground 零 props，Login 仅 import + 挂载"
  - "不改动 LoginForm / FeishuLoginPanel / 返回首页 Link 任何业务逻辑（scope guard）"

patterns-established:
  - "装饰层组件 + Fragment 并列模式：<ParticleBackground /> 与 <main> 以 Fragment 并列，互不嵌套，语义清晰"

requirements-completed:
  - LOGIN-02 (UAT approved 2026-04-20)
  - LOGIN-03 (UAT approved 2026-04-20)

# Metrics
duration: ~2min automated + manual UAT
completed: 2026-04-20
status: done

# UAT outcome
uat-approved: true
uat-hotfix:
  - "Login.tsx: removed opaque `background: 'var(--color-bg-page)'` from <main> so z-index:0 Canvas is visible. Body background (index.css line 62) still provides the page fallback color, including for prefers-reduced-motion."
---

# Phase 28 Plan 02: ParticleBackground 集成到 Login.tsx Summary（部分完成，待 UAT）

**将 ParticleBackground 组件以 Fragment 顶层挂载接入 Login 页，并给 `<main>` 施加 `position: relative + zIndex: 1` 激活 z-index 层叠；自动化 tsc/build 全通过；22 项 UAT checklist 等待人工浏览器验证。**

## Performance

- **Duration (automated):** ~2 min
- **Started:** 2026-04-20T06:24:21Z
- **Automated completed:** 2026-04-20T06:25:55Z
- **Tasks executed:** 1 of 2 (Task 2 = checkpoint:human-verify 阻塞中)
- **Files created:** 1 (本 SUMMARY，partial)
- **Files modified:** 1 (`frontend/src/pages/Login.tsx`)

## Accomplishments

- Task 1 完成：Login.tsx 成功 `import { ParticleBackground } from '../components/common/ParticleBackground'`，在 `return` 顶层以 Fragment 挂载，并给 `<main>` 增加 `position: 'relative'` 与 `zIndex: 1`
- TypeScript strict 模式编译通过：`cd frontend && npx tsc --noEmit` exit 0（无输出）
- 生产构建通过：`cd frontend && npm run build` exit 0（801 modules transformed, 3.47s）
- 所有 acceptance_criteria grep 条件命中（见 Self-Check）
- 登录页既有交互代码路径 **零改动**：LoginForm、FeishuLoginPanel、`<Link to="/">`、`handleLogin`、`useState` 均未被触碰

## Task Commits

1. **Task 1: Login.tsx 集成 ParticleBackground + z-index 调整** — `5909389` (feat)
   - `feat(28-02): mount ParticleBackground in Login.tsx with z-index:1 main`

2. **Task 2: 手动 UAT** — `checkpoint:human-verify`，pending human approval（22 项浏览器级验收清单）

## Files Modified

### `frontend/src/pages/Login.tsx`

Diff 摘要（+44 / -40）：

1. 顶部 imports 新增：
   ```ts
   import { ParticleBackground } from '../components/common/ParticleBackground';
   ```
   （位于 `LoginForm` 之后、`useAuth` 之前；保持"third-party → 相对 → type-only"顺序）

2. `return` 结构调整：
   - 外层从单一 `<main>` 改为 `<>...</>` Fragment 包裹
   - Fragment 内先挂载 `<ParticleBackground />`，再渲染 `<main>`
   - `<main>` 内联 style 追加两个属性：`position: 'relative'`、`zIndex: 1`
   - `background`、`display`、`alignItems`、`minHeight`、`padding` 等原属性全部保留
   - 两个 `<section className="surface animate-fade-up">` 及其内部内容字面未改，仅缩进随新的外层嵌套层级同步增加两格

3. **未改动**：
   - `LoginForm` props、`FeishuLoginPanel` 调用方式、`<Link to="/">` 文案与跳转
   - `handleLogin`、`resolveError`、`useState`、`useNavigate`、`useLocation`、`useAuth`
   - 主标题"欢迎使用智能调薪平台"、副标题"登录平台"、角色介绍四卡、"账号由管理员开通。首次登录需先改密。"提示

## Decisions Made

全部沿用 CONTEXT.md 的 D-01..D-12 决策，本 Plan 未引入新决策。执行期间唯一实现细节：

- **Fragment 结构选择 `<>...</>`** 而非 `<React.Fragment>` 长写法，与项目 TSX 风格一致（已有代码中未见显式 React.Fragment）
- **内部内容缩进统一加两格** 以匹配新增 `<main>` 下多一层 `<div>` 后的自然嵌套层级；非语义变更

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

### Worktree rebase alignment

起始时 worktree HEAD=`6bb9b82`（只含 28-CONTEXT 与 STATE.md 更新），与 expected base `7a2c234`（包含 28-01 的 ParticleBackground.tsx + SUMMARY）分叉。尝试 `git rebase --onto` 在 `.planning/STATE.md` 触发合并冲突；按 `worktree_branch_check` fallback 规则 `git reset --hard 7a2c234...` 对齐到 expected base。结果：

- 丢弃的两个提交 `4dc67b1` (docs(28): capture phase context) 与 `6bb9b82` (docs(state): record phase 28 context session) 所记录的信息，已被 expected base 上的后续状态（含 28-01-SUMMARY 与 state 更新）完整覆盖，无语义丢失
- 副作用：`git status` 显示多个其他 worktree 遗留的未跟踪/已修改文件（`.claude/worktrees/*`、其他 page 文件等），均来自并行 worktree，不在本 Plan scope；未 add 未 commit

## Self-Check: PASSED

**文件存在：**
- `FOUND: frontend/src/pages/Login.tsx` (96 lines after edit)
- `FOUND: .planning/phases/28-particle-background/28-02-SUMMARY.md` (本文件 — partial)

**提交存在：**
- `FOUND: 5909389` feat(28-02): mount ParticleBackground in Login.tsx with z-index:1 main

**Acceptance criteria grep（全部命中，count=1 each）：**
- `import { ParticleBackground } from` ✓
- `<ParticleBackground` ✓
- `zIndex: 1` ✓
- `position: 'relative'` ✓
- `<LoginForm` ✓（未被误删）
- `<FeishuLoginPanel` ✓（未被误删）
- `欢迎使用智能调薪平台` ✓（文案未被误改）
- Fragment 对：`<>` L50 + `</>` L93 ✓

**编译与构建：**
- `cd frontend && npx tsc --noEmit` exit=0（无输出）✓
- `cd frontend && npm run build` exit=0（801 modules, dist/assets/index-*.js 1847.49 kB gzip 574.58 kB）✓

**scope 保持：**
- `git diff 7a2c234 -- frontend/src/pages/Login.tsx` 仅包含 import 新增 + Fragment 包裹 + zIndex 两个属性 ✓
- 未触碰 `frontend/src/components/auth/LoginForm.tsx`、`FeishuLoginPanel.tsx` ✓

## Pending — Task 2（checkpoint:human-verify，UAT 22 项清单）

执行者不得越过此 checkpoint 自行推进；必须人工在浏览器中按下列 22 项逐项验证。本 SUMMARY 会在 UAT 通过后追加最终状态。

### 准备步骤

```bash
cd frontend
npm run dev
```

浏览器访问 `http://127.0.0.1:5174/login`。

### 验收项 A — Success Criteria #1（全屏 Canvas 粒子 + 连线）
- [ ] 1. 页面背景出现蓝色粒子（`#1456F0` 系）
- [ ] 2. 粒子在视口内浮动，接触视口边缘时反弹/折返
- [ ] 3. 邻近粒子间有细线连接，距离越近越明显
- [ ] 4. Canvas 填满整个视口，resize 后粒子数量合理（宽屏多、窄屏少）

### 验收项 B — Success Criteria #2（鼠标排斥）
- [ ] 5. 鼠标在页面空白区域移动时，约 120px 范围内粒子被推离
- [ ] 6. 鼠标静止时粒子继续自由浮动
- [ ] 7. 鼠标移出窗口后不再有排斥效果

### 验收项 C — Success Criteria #3（HiDPI + reduced-motion）
- [ ] 8. Retina/2x DPR 下粒子与连线清晰无锯齿
- [ ] 9. 开启「减少动态效果」→ 粒子消失，纯 `--color-bg-page` 灰底，表单仍可登录
- [ ] 10. 关闭「减少动态效果」刷新 → 粒子背景恢复

### 验收项 D — z-index / pointer-events 回归（D-03 验证）
- [ ] 11. 邮箱输入框可点击并 focus
- [ ] 12. 提交登录表单（即使账号密码错误）可看到后端返回的错误提示
- [ ] 13. 点击「飞书登录」按钮可跳转或显示既有行为
- [ ] 14. 点击「查看系统说明」Link 导航到 `/`
- [ ] 15. hover 到卡片区域不影响粒子行为（卡片覆盖 Canvas）

### 验收项 E — 标签页可见性暂停（D-12 验证）
- [ ] 16. Performance 录制期间切换 tab → 切出期间无 Animation Frame 事件
- [ ] 17. 切回登录页后 rAF 恢复

### 验收项 F — 触屏模式（D-09 验证）
- [ ] 18. `(pointer: coarse)` 模拟下刷新
- [ ] 19. 鼠标移动不再触发粒子排斥（仅浮动 + 连线）

### 验收项 G — 控制台与性能
- [ ] 20. Console 无报错无 warning
- [ ] 21. Performance 帧率 ≈ 60fps，CPU 合理
- [ ] 22. 路由切换后无事件监听器泄漏（Memory snapshot 验证）

**UAT outcome (2026-04-20): `approved`**

One hotfix applied before approval:
- `<main>` had `background: var(--color-bg-page)` which was opaque `#F5F6F8` and covered the z-index:0 Canvas. Removed that inline background; body (`index.css:62`) still supplies `--color-bg-page` as the page fallback, including when `ParticleBackground` returns `null` under prefers-reduced-motion. Committed separately as `fix(28-02): ...`.

## Next Phase Readiness

- 等待 UAT 通过
- UAT 通过后，Phase 28 完成；本 SUMMARY 补写最终结论段落并将 `status` 改为 `done`
- Phase 29（登录页重设计整合）可立即开工：z-index:0 Canvas + z-index:1 主内容方案已实战验证

## 手动 DevTools 验证（partial）

本轮自动化阶段不涉及浏览器级验证。所有核心集成属性通过以下静态手段覆盖：

1. TypeScript 严格模式编译通过
2. Vite 生产构建通过
3. acceptance_criteria 的 7 个 grep 条件 + Fragment 配对 + tsc + build 共计 10 项全命中
4. `git diff` 显示 Login.tsx 改动边界清晰，未越权改动 LoginForm / FeishuLoginPanel / Link

**待 UAT 补充验证：** Success Criteria #1/#2/#3 的运行时行为、D-03/D-09/D-12 的浏览器端回归、性能与无泄漏。

---
*Phase: 28-particle-background*
*Plan: 02*
*Status: done — Task 1 commit = 5909389; Task 2 UAT approved 2026-04-20 (one hotfix applied)*
