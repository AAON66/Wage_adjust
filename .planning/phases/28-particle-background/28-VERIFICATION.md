---
phase: 28-particle-background
verified: 2026-04-20T00:00:00Z
status: passed
score: 3/3 must-haves verified (roadmap SC) + 18/18 PLAN truths verified
re_verification:
  is_re_verification: false
requirements_verified:
  - id: LOGIN-02
    status: satisfied
    evidence: "登录页挂载 <ParticleBackground />，Canvas 全屏、蓝色 #1456F0 粒子 + 距离阈值连线 + UAT 22 项通过"
  - id: LOGIN-03
    status: satisfied
    evidence: "鼠标排斥（D-07/D-08）+ devicePixelRatio 缩放（D-11）+ prefers-reduced-motion return null（D-10）均落地并通过 UAT"
---

# Phase 28: 登录页粒子背景 Verification Report

**Phase Goal:** 登录页具备全屏 Canvas 粒子动态背景，提供现代化视觉体验
**Verified:** 2026-04-20
**Status:** passed
**Re-verification:** No — initial verification
**UAT:** 2026-04-20 由用户回复 `approved`（22 项浏览器级清单全部通过）

## Goal Achievement

### Observable Truths — ROADMAP Success Criteria（3 项）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | 登录页显示全屏 Canvas 粒子动态背景，粒子间有连线效果 | VERIFIED | `ParticleBackground.tsx:125` clamp(40,150) 粒子数；`:184-192` 距离 < 120px 绘制连线，α 线性衰减；`Login.tsx:51` 挂载；UAT A/1-4 通过 |
| SC-2 | 鼠标移动时粒子产生跟随交互效果 | VERIFIED | `ParticleBackground.tsx:145-152` 鼠标排斥力公式 `(INTERACTION_RADIUS - distM) / INTERACTION_RADIUS * REPEL_STRENGTH`；`:223-226` mousemove 监听；UAT B/5-7 通过 |
| SC-3 | 粒子背景在 HiDPI 屏幕上清晰不模糊，在 prefers-reduced-motion 开启时自动停止动画 | VERIFIED | `ParticleBackground.tsx:112-121` DPR 缩放 `canvas.width = cssW*dpr; ctx.scale(dpr,dpr)`；`:61-77` reduced-motion useState + change 监听 + `:256-259` return null；UAT C/8-10 通过 |

**Score (ROADMAP SC):** 3/3 ✓

### Observable Truths — PLAN 01 must_haves（10 项）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P1-1 | ParticleBackground 文件存在并默认导出一个 React 组件 | VERIFIED | `ParticleBackground.tsx:59` `export function ParticleBackground()` |
| P1-2 | 挂载后在 DOM 中插入一个 `<canvas>`，样式 position:fixed / inset:0 / z-index:0 / pointer-events:none | VERIFIED | `:261-275` JSX 符合全部四项（top:0, left:0, width:100vw, height:100vh, zIndex:0, pointerEvents:'none'） |
| P1-3 | 粒子数量按视口面积自适应，落在 [40, 150] 区间内 | VERIFIED | `:125` `Math.max(40, Math.min(150, Math.floor((cssW*cssH) / 15000)))` |
| P1-4 | 两粒子距离 < 120px 时绘制连线，透明度线性衰减 | VERIFIED | `:184-192` `if (dist < LINK_DISTANCE)` + α = `(1 - dist/LINK_DISTANCE) * LINK_BASE_ALPHA` |
| P1-5 | 鼠标移动时 120px 半径内的粒子被推离 | VERIFIED | `:145-152` 方向向量 + 距离反比位移 |
| P1-6 | prefers-reduced-motion: reduce 命中时 return null | VERIFIED | `:256-259` `if (reducedMotion) return null` + `:61-65` 初值 |
| P1-7 | HiDPI 使用 devicePixelRatio 缩放 | VERIFIED | `:112-121` resize 中 dpr scaling |
| P1-8 | document.visibilitychange 隐藏时暂停 rAF，可见时恢复 | VERIFIED | `:215-221` onVisibility；`:202-213` start/stop 围绕 rafId |
| P1-9 | 组件卸载时清理 rAF、所有事件监听器、媒体查询 listener | VERIFIED | `:76` mq removeEventListener；`:244-253` cleanup 含 cancelAnimationFrame + 4 处 removeEventListener |
| P1-10 | (pointer: coarse) 命中时不绑定 mousemove | VERIFIED | `:107-108` `const useMouse = !coarseQuery.matches`；`:236-239` if (useMouse) |

**Score (PLAN 01):** 10/10 ✓

### Observable Truths — PLAN 02 must_haves（8 项）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P2-1 | 登录页顶层挂载 `<ParticleBackground />` | VERIFIED | `Login.tsx:51` |
| P2-2 | `<main>` 在 z-index 层级上位于 Canvas 之上（z-index ≥ 1） | VERIFIED | `Login.tsx:52` `position: 'relative', zIndex: 1` |
| P2-3 | LoginForm（邮箱密码登录）点击/输入/提交功能不受影响 | VERIFIED | `Login.tsx:78` `<LoginForm ... onSubmit={handleLogin}>` 未改；UAT D/11-12 通过 |
| P2-4 | FeishuLoginPanel 所有按钮可点击，回调跳转正常 | VERIFIED | `Login.tsx:80` `<FeishuLoginPanel />` 未改；UAT D/13 通过 |
| P2-5 | Link（返回平台首页）可点击跳转 | VERIFIED | `Login.tsx:86` `<Link to="/">` 未改；UAT D/14 通过 |
| P2-6 | reduced-motion 场景下页面仍能完整登录 | VERIFIED | ParticleBackground return null + body background（`index.css:62`）兜底；UAT C/9 通过 |
| P2-7 | HiDPI 屏幕上 Canvas 清晰不模糊 | VERIFIED | UAT C/8 通过（用户实机验证） |
| P2-8 | 鼠标移动到 Canvas 范围产生粒子排斥效果 | VERIFIED | UAT B/5-7 通过（用户实机验证） |

**Score (PLAN 02):** 8/8 ✓

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/common/ParticleBackground.tsx` | 150–300 行 Canvas 粒子背景，含 export function ParticleBackground | VERIFIED | 277 行；`export function ParticleBackground()` @ L59；落在 min_lines ≥ 150 要求内 |
| `frontend/src/pages/Login.tsx` | 集成 ParticleBackground 的登录页 | VERIFIED | 96 行；含 `<ParticleBackground />` @ L51，`zIndex: 1` + `position: 'relative'` @ L52 |

gsd-tools `verify artifacts` 两个 PLAN 均 `all_passed: true, passed: 1/1`。

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| ParticleBackground.tsx | window.matchMedia('(prefers-reduced-motion: reduce)') | useEffect + change 监听 | WIRED | L64 初值，L73-76 mq.addEventListener('change', handler) + cleanup |
| ParticleBackground.tsx | document.visibilitychange | addEventListener('visibilitychange') | WIRED | L235 addEventListener，L247 removeEventListener cleanup |
| ParticleBackground.tsx | window.devicePixelRatio | canvas.width = cssWidth * DPR; ctx.scale(DPR, DPR) | WIRED | L112 dpr 读取，L115-116 canvas 内部分辨率 × dpr，L121 ctx.scale |
| Login.tsx | frontend/src/components/common/ParticleBackground | ES module import | WIRED | L7 import + L51 挂载 |
| Login.tsx `<main>` | z-index 层级 | position: relative + zIndex: 1 | WIRED | L52 内联 style 双属性 |

注：gsd-tools `verify key-links` 对 PLAN 01 三条链报 `Source file not found`，原因是 PLAN frontmatter 用裸文件名 `ParticleBackground.tsx` 而非相对路径；通过直接 grep 已确认全部 pattern 命中（`prefers-reduced-motion` 4×、`visibilitychange` 3×、`devicePixelRatio` 2×、`(pointer: coarse)` 3×）。工具报告属已知元数据解析边界，不代表真实缺失。

### Data-Flow Trace (Level 4)

ParticleBackground 不渲染"动态业务数据"——它是纯装饰层，数据源为：

1. **CSS custom property `--color-primary`** → `getComputedStyle(document.documentElement)` @ L95-97 读取 → `hexToRgb` @ L98 解析 → 粒子/连线 fillStyle/strokeStyle
   - 已验证 `index.css:13` `--color-primary: #1456F0` 存在
   - Fallback `'#1456F0'` 在 CSS 变量缺失时兜底（L97）
   - **Status: FLOWING** — CSS token 确实流向渲染，UAT A/1 确认"蓝色粒子"与品牌色一致
2. **浏览器 API（DPR、matchMedia、rAF、visibility）** → 组件状态 → Canvas 绘制
   - 无需外部数据；纯算法生成
   - **Status: FLOWING** — 全部 D-01..D-12 决策在源码中落地

登录页主内容（`<main>` / `<LoginForm>` / `<FeishuLoginPanel>`）的数据流不在本 Phase 范围，Plan 02 明确声明零业务逻辑改动，UAT D/11-14 已端到端验证表单提交与导航不受集成影响。

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| TypeScript 严格模式编译通过 | `cd frontend && npx tsc --noEmit` | exit 0 | PASS |
| 生产构建通过 | `cd frontend && npm run build` | exit 0, 801 modules | PASS |
| ParticleBackground 被 Login.tsx 引用 | grep import | L7 命中 1 次 | PASS |
| 源文件行数在合理区间 | wc -l | 277 行（目标 150–300） | PASS |
| cleanup block 无泄漏 | grep removeEventListener + cancelAnimationFrame | 4× remove + 1× cancel（T-28-02 要求） | PASS |

浏览器运行时行为（帧率、rAF 暂停、reduced-motion 切换、coarse pointer）不由静态检查覆盖，**已由 UAT 22 项清单替代执行**，用户 2026-04-20 回复 `approved`。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| LOGIN-02 | 28-01, 28-02 | 登录页添加全屏 Canvas 粒子动态背景，参考智慧树风格 | SATISFIED | ParticleBackground.tsx 277 行 + Login.tsx 挂载 + UAT 22 项通过；蓝色 #1456F0 稀疏粒子 + 连线 = 智慧树风格观感 |
| LOGIN-03 | 28-01, 28-02 | 粒子背景支持鼠标跟随交互、HiDPI 适配和 prefers-reduced-motion 响应 | SATISFIED | 鼠标排斥 @ L145-152、DPR scaling @ L112-121、reduced-motion return null @ L256-259；UAT B/C 项通过 |

**Phase 28 REQUIREMENTS.md 映射:** LOGIN-02 + LOGIN-03 两条均由本 Phase 覆盖；LOGIN-01（双栏布局）与 LOGIN-04（邮密登录保留）属 Phase 29 职责，非本 Phase scope。无遗漏、无越权。

无 orphaned 需求（两条全部在 PLAN 01 + PLAN 02 的 `requirements:` 字段中声明）。

### Anti-Patterns Scan

对 Phase 28 修改的两个文件执行扫描：

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| ParticleBackground.tsx | — | 无 TODO/FIXME/placeholder | — | — |
| ParticleBackground.tsx | — | 无空实现（return null 仅在 reduced-motion 场景，属 D-10 明示行为，非 stub） | — | — |
| ParticleBackground.tsx | 100, 101 | `let particles: Particle[] = [];`、`let rafId: number | null = null;` 初始化后立即由 resize()/start() 写入，不是未连线状态 | Info | 非 stub，属 rAF pattern 正常初值 |
| Login.tsx | — | 无 TODO/FIXME；`return <div>No...</div>` 等 placeholder 均无 | — | — |
| Login.tsx | — | handleLogin 完整实现（try/catch + login + navigate + forcePasswordChange 分支），非 console.log-only | — | — |

无 blocker、无 warning。组件为装饰层，`aria-hidden="true"` + `pointerEvents: 'none'` 恰当声明（符合无障碍最佳实践）。

### Hotfix 合理性验证

Plan 02 Task 1 原本给 `<main>` 保留了 `background: 'var(--color-bg-page)'`，但该值 `#F5F6F8` 为不透明色，叠在 `z-index: 0` 的 Canvas 之上会完全遮挡粒子。Hotfix `3249fa1` 从 `<main>` 移除该属性，依赖 `index.css:62` 的 body `background: var(--color-bg-page)` 作为页面兜底（已确认存在）。

- **正确性：** body 背景在 `<main>` 透明后仍覆盖整个视口，reduced-motion 场景下 ParticleBackground return null 不渲染 Canvas，此时 body 的 `#F5F6F8` 灰底正是 fallback 预期（D-10 原设计意图）
- **回归风险：** 无 — 登录页原本即以 body 为底色，`<main>` 的 background 是冗余
- **测试证据：** UAT C/9（reduced-motion 下仍为 `--color-bg-page` 灰底且表单可登录）通过

### Human Verification Required

**None.** 22 项浏览器级 UAT 清单已由用户于 2026-04-20 完成并回复 `approved`，覆盖 Success Criteria #1/#2/#3 + D-03/D-09/D-12 所有运行时行为。

## Gaps Summary

无。Phase 28 goal 已达成：

- 3 项 ROADMAP Success Criteria 全部落地并通过 UAT
- 18 项 PLAN must_haves（10 + 8）全部验证通过
- 2 条需求（LOGIN-02、LOGIN-03）在代码中有完整证据
- TypeScript 严格模式编译通过、生产构建通过
- cleanup block 满足 T-28-02 零泄漏要求
- 一处 hotfix（`<main>` 透明化）已通过验证，无回归风险

Phase 28 status: **complete**。可以推进 Phase 29（登录页重设计整合），其中 Success Criteria #3「粒子动态背景作为全屏底层正确显示，不遮挡登录内容」的基础设施已在本 Phase 就绪（z-index:0 + pointer-events:none + reduced-motion fallback 均已实战验证）。

---

*Verified: 2026-04-20*
*Verifier: Claude (gsd-verifier)*
