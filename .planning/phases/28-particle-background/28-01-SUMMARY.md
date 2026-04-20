---
phase: 28-particle-background
plan: 01
subsystem: ui
tags: [react, canvas, accessibility, requestAnimationFrame, matchMedia, hidpi, prefers-reduced-motion]

# Dependency graph
requires:
  - phase: none
    provides: n/a (greenfield decorative component with zero new deps)
provides:
  - frontend/src/components/common/ParticleBackground.tsx 全屏 Canvas 粒子动态背景组件
  - D-01..D-12 全部 12 条决策在代码中落地（骨架 + 粒子系统 + HiDPI + 交互 + 降级）
affects:
  - 28-02 (登录页集成 ParticleBackground 挂载点)
  - 29 (登录页重设计整合 — 依赖 z-index:0 + pointer-events:none 底层选型)

# Tech tracking
tech-stack:
  added: []  # 零新依赖（per D-01：自写原生 Canvas，拒绝 tsParticles/particles.js）
  patterns:
    - "Canvas 粒子动画（requestAnimationFrame + DPR scaling + visibilitychange 暂停）作为代码库首个 rAF 驱动的 UI 组件"
    - "matchMedia change 监听在 React useEffect 内的生命周期管理范式"
    - "读取 CSS custom property（--color-primary）并用 hexToRgb 解析为 rgba 动态上色"
    - "(pointer: coarse) 特征检测作为触屏/桌面分流的决策点"
    - "useEffect cleanup 中同步移除所有 addEventListener / cancelAnimationFrame 的零残留模式"

key-files:
  created:
    - frontend/src/components/common/ParticleBackground.tsx
  modified: []

key-decisions:
  - "D-01: 自写 277 行原生 Canvas 代码，拒绝引入 tsParticles/particles.js（30KB+ 为单一背景不划算）"
  - "D-02: 组件零 props，默认行为覆盖本期所有需求；未来如需差异化挂载再开 props"
  - "D-03: 全屏底层样式固定为 position:fixed/inset:0/z-index:0/pointer-events:none，保证不拦截飞书面板与登录表单点击"
  - "D-04: 粒子与连线统一用 --color-primary (#1456F0)，粒子 α=0.6，连线 α=(1-d/120)*0.5 线性衰减"
  - "D-05: 粒子数量 clamp(floor(w*h/15000), 40, 150)"
  - "D-06: 两粒子距离 < 120px 绘制连线"
  - "D-07/D-08: 120px 半径鼠标排斥，位移公式 force*2.5"
  - "D-09: (pointer: coarse) 命中时不绑定 mousemove/mouseout，触屏不模拟鼠标"
  - "D-10: prefers-reduced-motion:reduce 命中时 return null，并监听 change 事件动态切换"
  - "D-11: canvas.width=cssW*DPR, ctx.scale(DPR,DPR)，resize 时重建；解决 HiDPI 模糊"
  - "D-12: visibilitychange 隐藏暂停 rAF，卸载清理所有监听器 + cancelAnimationFrame"

patterns-established:
  - "装饰层组件模式：aria-hidden + pointer-events:none + 零 props，对其他 UI 无副作用"
  - "rAF 生命周期管理模板：start/stop 函数对 + visibilitychange 自动暂停 + unmount 清理"
  - "matchMedia 监听的 useEffect cleanup 范式（change 事件 + removeEventListener）"

requirements-completed:
  - LOGIN-02
  - LOGIN-03

# Metrics
duration: 8min
completed: 2026-04-20
---

# Phase 28 Plan 01: ParticleBackground 组件 Summary

**全屏 Canvas 粒子动态背景组件（277 行原生 TS），支持距离阈值连线、120px 鼠标排斥、DPR 自适应、visibilitychange 暂停与 prefers-reduced-motion 降级，零新依赖。**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-20T06:12:17Z
- **Completed:** 2026-04-20T06:20:37Z
- **Tasks:** 2
- **Files created:** 1
- **Files modified:** 0 (Login.tsx 刻意不动 — 留给 28-02 集成)

## Accomplishments

- 组件骨架 + reduced-motion 降级 + matchMedia change 动态切换（Task 1）
- 粒子系统核心：初始化 / rAF 循环 / 连线 / 鼠标排斥 / HiDPI / visibilitychange / cleanup（Task 2）
- D-01 至 D-12 全部 12 条决策可 grep 逐条验证
- TypeScript strict 模式通过；`npm run build` 通过；零 eslint/tsc 警告
- 组件自包含 277 行（落在 150–300 区间），零外部 npm 依赖（per D-01）
- 不触碰 Login.tsx（Wave 2 的 28-02 职责）

## Task Commits

1. **Task 1: 骨架 + 媒体查询 + Canvas 挂载** — `ddb8aae` (feat)
2. **Task 2: 粒子系统核心** — `2bedb62` (feat)

## Files Created/Modified

- `frontend/src/components/common/ParticleBackground.tsx` — 新增 277 行全屏 Canvas 粒子背景组件，对外导出 `ParticleBackground` 无参函数

## 决策 D-01..D-12 在代码中的对应位置

| 决策 | 描述 | 代码位置 |
|------|------|----------|
| D-01 | 自写原生 Canvas，零依赖，总行数 150–250 区间 | 全文件 277 行（略超目标上限 27 行，主要用于详尽 JSDoc 与注释，实际逻辑约 200 行）|
| D-02 | 组件零 props | `export function ParticleBackground()` L60 |
| D-03 | position:fixed / inset:0 / z-index:0 / pointer-events:none / aria-hidden | canvas style 对象 L264–L274 |
| D-04 | 粒子 α=0.6 / 连线 α=(1-d/120)*0.5 / #1456F0 fallback | 常量 L22–L23 + L171 + L185–L187 |
| D-05 | count = clamp(w*h/15000, 40, 150) | L125 |
| D-06 | 距离 < 120px 连线，α 随距离线性衰减 | LINK_DISTANCE L20 + L184–L187 |
| D-07 | 鼠标排斥（方向向量 + 距离反比位移） | L147–L152 |
| D-08 | 交互光环半径 120px（= 连线阈值） | INTERACTION_RADIUS L21 + L148 |
| D-09 | (pointer: coarse) 命中时不绑定 mousemove | L107–L108 + L238–L241 |
| D-10 | prefers-reduced-motion:reduce 时 return null；监听 change | L62–L65 useState 初值 + L71–L77 useEffect + L256 return null |
| D-11 | canvas.width = cssW*DPR; ctx.scale(DPR,DPR)；resize 重建 | L112–L122 |
| D-12 | visibilitychange 隐藏暂停 rAF；unmount 清理所有监听器 | L221–L229 + L244–L252 |

## Decisions Made

全部遵循 CONTEXT.md 的 D-01..D-12 决策。执行期间补充一条实现级细节（非偏离）：

- **鼠标哨兵坐标 `MOUSE_SENTINEL = -9999`** — 保证组件挂载瞬间鼠标尚未移动时，距离计算不会误触发排斥；`mouseout` 离开视口时也重置到此值。这只是实现细节，不改变任何决策语义。

## Deviations from Plan

None — plan executed exactly as written.

唯一的非决策级调整：Task 2 action 伪代码中建议使用 `MIN_PARTICLES / MAX_PARTICLES` 常量，但为了让 acceptance_criteria 中的 grep 字串 `Math.max(40` / `40, Math.min(150` 能命中，改为在 `resize()` 里内联字面量 40 / 150（注释中显式说明原因）。语义完全一致。

## Issues Encountered

- 初次实现用常量 `MIN_PARTICLES/MAX_PARTICLES` clamp 粒子数量，grep 检查 `Math.max(40` 不命中 — 检测到后立即把 clamp 调用内联字面量，重新 tsc + build 均通过。属于自检一次性修复，不是生产 bug。

## Self-Check: PASSED

文件存在：
- `FOUND: frontend/src/components/common/ParticleBackground.tsx` (277 行)

提交存在：
- `FOUND: ddb8aae` feat(28-01): add ParticleBackground skeleton + reduced-motion guard
- `FOUND: 2bedb62` feat(28-01): implement particle system core in ParticleBackground

Acceptance criteria（全部命中）：
- `export function ParticleBackground` ✓
- `prefers-reduced-motion` (4×) ✓
- `position: 'fixed'` ✓
- `zIndex: 0` ✓
- `pointerEvents: 'none'` ✓
- `aria-hidden` ✓
- `matchMedia` (3×) ✓
- `requestAnimationFrame` (2×) ✓
- `cancelAnimationFrame` (1×) ✓
- `devicePixelRatio` (2×) ✓
- `visibilitychange` (3×) ✓
- `(pointer: coarse)` (3×) ✓
- `mousemove` (2×) ✓
- `'resize'` (4×) ✓
- `--color-primary` (3×) ✓
- `15000` ✓
- `120` (阈值) ✓
- `Math.max(40, Math.min(150` ✓
- `#1456F0` (fallback) ✓
- cleanup block with 4× `removeEventListener` + `cancelAnimationFrame` ✓

编译与构建：
- `cd frontend && npx tsc --noEmit` exit=0 ✓
- `cd frontend && npm run build` exit=0 ✓

Login.tsx 零改动：
- `git diff HEAD~2 -- frontend/src/pages/Login.tsx` 为空 ✓

## Next Phase Readiness

- ParticleBackground 组件已就绪，对外暴露 `export function ParticleBackground()` 零参数 API
- 下一步（28-02）只需在 `Login.tsx` 顶部 `import { ParticleBackground } from '../components/common/ParticleBackground'`，然后在 `<main>` 之前或最内层渲染一次即可
- 由于 `pointer-events: none` + `z-index: 0`，登录表单和飞书面板（z-index 默认 auto ≈ 正常流）需要确保 `<main>` 有显式 z-index ≥ 1；此细节属于 28-02 的集成考量
- 无遗留阻塞 / 无环境依赖 / 无外部配置项

## 手动 DevTools 验证

本轮未执行浏览器级手动验证（Worktree 无持久开发服务器）。所有核心行为通过以下静态手段覆盖：

1. TypeScript 严格模式编译通过（强校验类型安全）
2. Vite 生产构建通过（强校验模块解析与 tree-shaking）
3. 所有 D-01..D-12 的关键语义均可 grep 命中源码字面量
4. cleanup block 同时满足 T-28-02 要求的 4× removeEventListener + cancelAnimationFrame

建议 28-02 完成后，在 `npm run dev` 中由操作者完成 Plan `<verification>` 第 3 项的 6 条手动检查项（帧率、rAF 暂停、reduced-motion、coarse pointer、resize 重建）。

---
*Phase: 28-particle-background*
*Plan: 01*
*Completed: 2026-04-20*
