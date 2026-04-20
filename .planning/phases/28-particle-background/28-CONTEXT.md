# Phase 28: 登录页粒子背景 - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

交付一个可复用的 Canvas 全屏粒子动态背景组件 `ParticleBackground`，并由 `Login.tsx` 挂载为底层视觉。组件须满足：粒子浮动 + 粒子间距离阈值连线 + 鼠标排斥交互 + HiDPI 清晰 + `prefers-reduced-motion` 降级 + 标签页隐藏暂停。

**In scope:**
- 新增 `frontend/src/components/common/ParticleBackground.tsx`
- 在 `frontend/src/pages/Login.tsx` 顶部挂载一次

**Out of scope（延至 Phase 29）:**
- 登录页左右双栏布局重构
- 其他页面的粒子背景复用
- Canvas 之外的登录页 UI 变动（飞书面板、登录表单、角色介绍卡片）

</domain>

<decisions>
## Implementation Decisions

### 实现方式
- **D-01:** 自写原生 Canvas 代码（目标 150-250 行 TS），**不**引入 `tsParticles` / `particles.js`。项目既有前端依赖仅 axios/react/react-router/tailwind，为单一登录页背景引入 30KB+ 库属过度引入。
- **D-02:** 组件形态为独立可复用组件 `frontend/src/components/common/ParticleBackground.tsx`，对外暴露极少 props（允许默认全走内置常量；若出现差异化挂载点再开 props）。默认行为覆盖本期所有需求。
- **D-03:** Canvas 以 `position: fixed; inset: 0; z-index: 0; pointer-events: none` 作为全屏底层，登录主内容 `z-index` 提升到 ≥ 1。`pointer-events: none` 保证不拦截登录表单和飞书面板的点击。

### 视觉风格
- **D-04:** 粒子与连线统一使用项目主色 `#1456F0`，透明度 rgba α ≈ 0.4–0.6 区间。避免多色/渐变以保持与品牌主色一致。
- **D-05:** 粒子数量按视口面积自适应：`count = clamp(floor(width * height / 15000), 40, 150)`。宽屏不稀疏，小屏不拥挤；设硬上限 150 防极端尺寸。
- **D-06:** 粒子间连线规则：两粒子距离 < 120px 时绘制；线条透明度按 `(1 - distance/120) * baseAlpha` 线性衰减。满足 Success Criteria #1「粒子间有连线效果」。

### 鼠标交互行为
- **D-07:** 交互模式为**排斥**——鼠标位置作为隐形光环，光环内粒子被推离（常见方向向量 + 距离反比位移）。满足 Success Criteria #2「鼠标跟随交互效果」。
- **D-08:** 交互光环半径 120px（与连线阈值一致，视觉节奏统一）。
- **D-09:** 触屏设备（`(pointer: coarse)` media query 命中）关闭鼠标交互，仅保留粒子自然浮动与连线。`touchmove` 不模拟鼠标，避免干扰滚动。

### 无障碍降级
- **D-10:** `prefers-reduced-motion: reduce` 命中时 `ParticleBackground` 组件直接 `return null`，不挂载 Canvas。登录页 fallback 为既有纯色 `--color-bg-page` 背景。监听该媒体查询的 `change` 事件，用户切换偏好时动态生效。满足 Success Criteria #3 后半段。
- **D-11:** HiDPI 适配：`canvas.width = cssWidth * DPR`、`canvas.height = cssHeight * DPR`、`canvas.style.{width,height} = cssPx`，绘制前 `ctx.scale(DPR, DPR)`。监听 `resize` 与 DPR 变化（窗口跨屏）并重建尺寸与粒子位置。满足 Success Criteria #3 前半段「HiDPI 清晰不模糊」。
- **D-12:** 监听 `document.visibilitychange`：标签页隐藏时取消 `requestAnimationFrame` 并暂停；可见时 resume。同时 unmount 时清理 rAF / 事件监听 / ResizeObserver，避免内存泄漏。

### Claude's Discretion
- 粒子单体尺寸（建议 1.5–3px 随机）
- 粒子初始速度区间、边界反弹 / 环绕策略（推荐反弹保持粒子在可视区）
- 粒子在排斥光环内的位移公式细节
- 动画帧率上限（推荐不额外 cap，交由浏览器 rAF 节流）
- 是否在 Canvas 初次挂载时做淡入（不影响功能，可加可不加）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与验收
- `.planning/ROADMAP.md` §"Phase 28: 登录页粒子背景" — 目标、依赖、Success Criteria 1/2/3
- `.planning/REQUIREMENTS.md` §"登录页重设计 (LOGIN)" — LOGIN-02（全屏 Canvas 粒子背景，参考智慧树风格）、LOGIN-03（鼠标跟随 + HiDPI + prefers-reduced-motion）

### 下游协调
- `.planning/ROADMAP.md` §"Phase 29: 登录页重设计整合" — Phase 29 Success Criteria #3「粒子动态背景作为全屏底层正确显示，不遮挡登录内容」。Phase 28 的 `z-index: 0` 与 `pointer-events: none` 选型已为此预留。

### 代码上下文
- `frontend/src/pages/Login.tsx` — 挂载位置
- `frontend/src/index.css` — 主色变量 `--color-primary: #1456F0`、页面底色 `--color-bg-page: #F5F6F8`
- `.planning/codebase/STRUCTURE.md`、`.planning/codebase/CONVENTIONS.md` — 前端组件与 hooks 组织约定

无外部 ADR / 独立 spec 文档——本 CONTEXT.md 即是本 Phase 的规范来源。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/index.css` CSS 变量：`--color-primary`（粒子主色来源）、`--color-bg-page`（reduced-motion 回退底色，已是登录页 `<main>` 当前 `background`）
- `.surface` / `.surface-subtle` / `.animate-fade-up` 既有样式类——Canvas 层与现有登录卡片视觉不冲突
- `frontend/src/hooks/useAuth.tsx`——hooks 目录存在，如后续拆分 `useParticleCanvas` 可遵循同一约定

### Established Patterns
- 前端组件以 `PascalCase.tsx` 命名，内部使用内联样式 + Tailwind 混用，严格 TS（`strict: true`）。`from __future__` 式文件顶部导入（前端习惯为 third-party → 相对 → type-only）
- 动画目前只靠 CSS（`animate-fade-up`），无 `requestAnimationFrame` 先例——本期为代码库首个 rAF 驱动的 Canvas 组件，需要给 researcher / planner 留下现代实现的清单（rAF、DPR、visibilitychange、matchMedia.change、cleanup）

### Integration Points
- 挂载点：`frontend/src/pages/Login.tsx` 顶部（最外层 `<main>` 之前或紧随其后），无需改动路由或 Provider
- 无后端依赖，无数据库迁移，无新 API
- 与 Phase 27 `FeishuLoginPanel` 共存——Canvas 须 `pointer-events: none` 保证扫码/表单点击生效

</code_context>

<specifics>
## Specific Ideas

- 参考风格：LOGIN-02 明确写"参考智慧树风格" —— 典型观感为蓝白基调、粒子稀疏、鼠标排斥、柔和连线。本期决策与该观感对齐。
- 性能红线：本期交付内容只在登录页展示，不出现在业务主流程中，因此可接受中等 CPU 开销，但 reduced-motion 与 visibility 暂停是硬要求，不可省略。

</specifics>

<deferred>
## Deferred Ideas

- **粒子背景跨页面复用** —— 若后续仪表板 / 员工门户希望复用粒子效果，属新需求，应作为独立 Phase / 子任务。当前 `ParticleBackground` 组件设计时保持纯展示 / 无业务耦合即可自然支持复用。
- **鼠标点击粒子炸开特效** —— 本期排斥 + 连线已满足 Success Criteria，点击炸开属锦上添花，不在此 Phase。
- **深色模式下的粒子配色** —— 项目目前无深色模式，等深色模式落地再统一处理。
- **FPS 自适应降级（低端设备帧率 < 30 时减粒子）** —— 可观测性不足，且面积自适应已能限制粒子数；若实测低端设备有掉帧再开专项优化。

</deferred>

---

*Phase: 28-particle-background*
*Context gathered: 2026-04-20*
